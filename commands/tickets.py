import nextcord
from nextcord.ext import commands, tasks
from collections import Counter
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import os

# Importar configuraciones y utilidades
from config import (
    OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID, TICKETS_CATEGORY_NAME,
    TICKETS_LOG_CHANNEL_ID, BRAND_NAME, OWNER_DISCORD_ID, GUILD_ID
)
from data_manager import load_data, save_data, get_next_ticket_id
from utils import is_staff, is_admin
from views.simple_ticket_view import SimpleTicketView
from views.base_ticket_view import enviar_transcripcion
from .ticket_helpers import TicketRateLimiter, format_ticket_embed

# Configurar logging
log = logging.getLogger(__name__)

def find_open_ticket(guild: nextcord.Guild, user_id: int):
    """Devuelve el id del ticket abierto del usuario, o None.
    Los tickets cuyo canal ya no existe (borrado a mano) se marcan cerrados para no bloquear al usuario."""
    data = load_data()
    open_ticket_id, changed = None, False
    for ticket_id, ticket in data["tickets"].items():
        if (ticket["user_id"] != str(user_id) or
            ticket["status"] not in ["abierto", "pausado"] or
            ticket.get("estado_detallado") in ["cerrado_por_owner", "cerrado_por_staff", "cerrado"]):
            continue
        if guild.get_channel(int(ticket["channel_id"])) is None:
            ticket["status"] = "cerrado"
            ticket["estado_detallado"] = "cerrado"
            ticket.setdefault("historial", []).append({
                "estado": "cerrado",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detalles": "Cerrado automáticamente: el canal ya no existe"
            })
            changed = True
            log.info(f"Ticket {ticket_id} cerrado automáticamente (canal inexistente)")
        else:
            open_ticket_id = ticket_id
    if changed:
        save_data(data)
    return open_ticket_id

# Cierre por inactividad: solo tickets "abierto" (pausados y completados no se tocan)
HORAS_AVISO_INACTIVIDAD = 48
HORAS_CIERRE_TRAS_AVISO = 24

def actualizar_ticket(ticket_id: str, cambios: dict):
    """Relee, cambia y guarda sin await de por medio, para no pisar cambios hechos por otros handlers."""
    data = load_data()
    if ticket_id in data["tickets"]:
        data["tickets"][ticket_id].update(cambios)
        save_data(data)

def resumen_staff(tickets: dict, desde: datetime):
    """Cuenta por miembro del staff los tickets tomados, completados y cerrados desde `desde`."""
    tomados, completados, cerrados = Counter(), Counter(), Counter()
    estados = Counter()
    for t in tickets.values():
        if datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc) < desde:
            continue
        estados[t["status"]] += 1
        if t.get("asignado_a"):
            tomados[t["asignado_a"]] += 1
        if t.get("completed_by"):
            completados[t["completed_by"]] += 1
        if t.get("closed_by"):
            cerrados[t["closed_by"]] += 1
    return estados, tomados, completados, cerrados

class SimpleTicketCommands(commands.Cog):
    """Sistema de tickets simplificado compatible con nextcord 2.6.0"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = TicketRateLimiter()  # Use helper class
        self.revisar_inactivos.start()

    def cog_unload(self):
        self.revisar_inactivos.cancel()

    @tasks.loop(hours=1)
    async def revisar_inactivos(self):
        """Avisa a las 48 h sin mensajes y cierra (con transcripción) 24 h después del aviso."""
        ahora = datetime.now(timezone.utc)
        for ticket_id, t in load_data()["tickets"].items():
            if t["status"] != "abierto":
                continue
            canal = self.bot.get_channel(int(t["channel_id"]))
            if canal is None:
                continue  # find_open_ticket se encarga de los fantasmas
            try:
                ultimo = nextcord.utils.snowflake_time(canal.last_message_id) if canal.last_message_id else canal.created_at
                horas = (ahora - ultimo).total_seconds() / 3600
                aviso = t.get("aviso_inactividad_msg")
                if aviso and canal.last_message_id != aviso:
                    actualizar_ticket(ticket_id, {"aviso_inactividad_msg": None})  # alguien escribió después del aviso
                    aviso = None

                if aviso and horas >= HORAS_CIERRE_TRAS_AVISO:
                    await enviar_transcripcion(canal, ticket_id, "cerrado por inactividad")
                    actualizar_ticket(ticket_id, {
                        "status": "cerrado",
                        "estado_detallado": "cerrado_por_inactividad",
                        "closed_at": ahora.isoformat(),
                    })
                    await canal.delete(reason=f"Ticket {ticket_id} cerrado por inactividad")
                    log.info(f"Ticket {ticket_id} cerrado por inactividad")
                elif not aviso and horas >= HORAS_AVISO_INACTIVIDAD:
                    msg = await canal.send(
                        f"<@{t['user_id']}> ⏰ Este ticket lleva {HORAS_AVISO_INACTIVIDAD} h sin actividad. "
                        f"Si nadie escribe en las próximas {HORAS_CIERRE_TRAS_AVISO} h se cerrará automáticamente."
                    )
                    actualizar_ticket(ticket_id, {"aviso_inactividad_msg": msg.id})
            except Exception as e:
                log.error(f"Error revisando inactividad de {ticket_id}: {e}")

    @revisar_inactivos.before_loop
    async def _esperar_bot(self):
        await self.bot.wait_until_ready()

    @nextcord.slash_command(name="stats_tickets", description="Estadísticas de tickets por staff (solo staff)", guild_ids=[GUILD_ID])
    async def stats_tickets(self, interaction: nextcord.Interaction, dias: int = 30):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        desde = datetime.now(timezone.utc) - timedelta(days=dias)
        estados, tomados, completados, cerrados = resumen_staff(load_data()["tickets"], desde)

        embed = nextcord.Embed(title=f"📊 Tickets de los últimos {dias} días", color=0x00E5A8,
                               timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Por estado",
                        value="\n".join(f"• {k}: **{v}**" for k, v in estados.most_common()) or "Sin tickets",
                        inline=False)
        staff = set(tomados) | set(completados) | set(cerrados)
        filas = sorted(staff, key=lambda u: -(cerrados[u] + completados[u]))
        embed.add_field(name="Por staff (tomados / completados / cerrados)",
                        value="\n".join(f"<@{u}>: {tomados[u]} / {completados[u]} / {cerrados[u]}" for u in filas)
                        or "Nadie ha tomado, completado ni cerrado tickets en este periodo",
                        inline=False)
        embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def _log_conversation(self, channel_id: int, user_id: int, message_content: str, author_name: str, message_type: str = "message"):
        """Registra conversaciones en archivos de log"""
        try:
            # Crear directorio de logs si no existe
            os.makedirs("logs", exist_ok=True)
            
            log_file = f"logs/ticket_{channel_id}.log"
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message_type.upper()} - {author_name} (ID: {user_id}): {message_content}\n")
                
        except Exception as e:
            log.error(f"Error logging conversation: {e}")
    
    @commands.command(name="panel")
    async def panel(self, ctx, canal: nextcord.TextChannel = None):
        """Comando para mostrar el panel de tickets"""
        if not is_staff(ctx.author):
            await ctx.send("❌ Solo el staff puede usar este comando.")
            return
        try:
            # Usar el canal especificado o el canal actual
            target_channel = canal or ctx.channel
            
            # Crear embed del panel
            embed = nextcord.Embed(
                title="🎫 Panel de Tickets - ONZA Bot",
                description="**¡Bienvenido a nuestro sistema de tickets!**\n\n"
                           "Selecciona el tipo de servicio que necesitas y crearemos un ticket privado para ti.\n"
                           "Un miembro del staff te atenderá pronto.\n\n"
                           "━━━━━━━━━━━━━━━━━━━━━━━━",
                color=0x00E5A8,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Información de servicios
            embed.add_field(
                name="📋 **Servicios Disponibles**",
                value="• **Discord Nitro/Basic:** Suscripciones premium\n• **Spotify:** Individual y Duo\n• **YouTube Premium:** Acceso sin anuncios\n• **Crunchyroll:** Anime y manga\n• **Robux:** Moneda virtual de Roblox\n• **Accesorios Discord:** Decoraciones y themes",
                inline=False
            )
            
            # Horario de atención
            embed.add_field(
                name="🕐 **Horario de Atención**",
                value="**10:00 AM - 10:00 PM** (Horario de México)",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
            
            # Crear vista con opciones de tickets
            view = SimpleTicketView(self)
            
            # Enviar mensaje
            await target_channel.send(embed=embed, view=view)
            
            # Confirmar al usuario
            await ctx.send(f"✅ Panel de tickets enviado a {target_channel.mention}")
            
            log.info(f"Panel de tickets enviado por {ctx.author.display_name} en {target_channel.name}")
            
        except Exception as e:
            await ctx.send("❌ Error al enviar el panel de tickets")
            log.error(f"Error en panel: {e}")
    
    @commands.command(name="ticket")
    async def ticket(self, ctx, tipo: str = "ayuda"):
        """Comando directo para crear tickets"""
        try:
            # Verificar cooldown y rate limiting
            can_create, seconds_remaining = self.rate_limiter.check_cooldown(ctx.author.id, OWNER_DISCORD_ID)
            if not can_create:
                minutes = seconds_remaining // 60
                seconds = seconds_remaining % 60
                await ctx.send(f"⏰ Debes esperar {minutes}m {seconds}s antes de crear otro ticket")
                return

            # Owner puede tener múltiples tickets abiertos
            if ctx.author.id != OWNER_DISCORD_ID:
                # Verificar si ya tiene un ticket abierto
                open_ticket_id = find_open_ticket(ctx.guild, ctx.author.id)
                if open_ticket_id:
                    await ctx.send(f"❌ Ya tienes un ticket abierto ({open_ticket_id}). Por favor, espera a que se resuelva o contacta al staff.")
                    return

            # Actualizar tracking del usuario
            self.rate_limiter.update_user_ticket_tracking(ctx.author.id)

            # Crear el ticket
            await self._create_ticket(ctx.guild, ctx.author, tipo, ctx)

        except Exception as e:
            await ctx.send("❌ Error al crear ticket")
            log.error(f"Error en ticket: {e}")
    
    async def _create_ticket(self, guild: nextcord.Guild, user: nextcord.Member, ticket_type: str, ctx):
        """Crea un ticket usando el sistema integrado"""
        try:
            log.info(f"🚀 Iniciando creación de ticket para {user.display_name} - Tipo: {ticket_type}")
            
            # Obtener o crear categoría de tickets
            category = None
            for cat in guild.categories:
                if cat.name.lower() == TICKETS_CATEGORY_NAME.lower():
                    category = cat
                    break
            
            if not category:
                log.info(f"📁 Creando categoría de tickets: {TICKETS_CATEGORY_NAME}")
                category = await guild.create_category(TICKETS_CATEGORY_NAME)
            else:
                log.info(f"📁 Usando categoría existente: {category.name}")
            
            # Crear canal de ticket
            ticket_number = get_next_ticket_id()
            channel_name = f"ticket-{ticket_number}-{user.display_name.lower().replace(' ', '-')}"
            log.info(f"🎫 Creando canal: {channel_name} (Ticket #{ticket_number})")
            
            # Permisos del canal
            overwrites = {
                guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Agregar roles de staff si existen
            if OWNER_ROLE_ID:
                owner_role = guild.get_role(OWNER_ROLE_ID)
                if owner_role:
                    overwrites[owner_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            if STAFF_ROLE_ID and STAFF_ROLE_ID != OWNER_ROLE_ID:
                staff_role = guild.get_role(STAFF_ROLE_ID)
                if staff_role:
                    overwrites[staff_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            if SUPPORT_ROLE_ID and SUPPORT_ROLE_ID not in [OWNER_ROLE_ID, STAFF_ROLE_ID]:
                support_role = guild.get_role(SUPPORT_ROLE_ID)
                if support_role:
                    overwrites[support_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            # Crear el canal
            log.info(f"🔧 Configurando permisos para {len(overwrites)} roles/usuarios")
            ticket_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number} - {user.display_name} - {ticket_type.title()}"
            )
            log.info(f"✅ Canal creado exitosamente: {ticket_channel.name} (ID: {ticket_channel.id})")
            
            # Registrar en la base de datos
            log.info(f"💾 Registrando ticket en base de datos...")
            data = load_data()
            ticket_id = f"ticket-{ticket_number}"
            data["tickets"][ticket_id] = {
                "user_id": str(user.id),
                "channel_id": str(ticket_channel.id),
                "ticket_type": ticket_type,
                "status": "abierto",
                "estado_detallado": "esperando_revision",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "historial": [{
                    "estado": "creado",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "detalles": "Ticket creado por el usuario"
                }]
            }
            save_data(data)
            log.info(f"✅ Ticket registrado en base de datos")
            
            # Crear embed de bienvenida
            embed = nextcord.Embed(
                title=f"🎫 Ticket #{ticket_number} - {ticket_type.title()}",
                description=f"Hola {user.mention}! Has abierto un ticket de **{ticket_type}**.\n\n"
                           f"**Información del ticket:**\n"
                           f"• **Usuario:** {user.display_name}\n"
                           f"• **Tipo:** {ticket_type.title()}\n"
                           f"• **Creado:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>\n\n"
                           f"Un miembro del staff te atenderá pronto. Mientras tanto, puedes describir tu consulta.",
                color=0x00E5A8,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Agregar información específica según el tipo
            if ticket_type == "discord":
                embed.add_field(
                    name="💬 Información para Discord",
                    value="**Responde:** plan + tu @Discord y método de pago\n\n**Planes disponibles:**\n• Nitro 1 año: $649\n• Nitro 1 mes: $90\n• Basic 1 año: $349\n• Basic 1 mes: $40",
                    inline=False
                )
            elif ticket_type == "spotify":
                embed.add_field(
                    name="🎵 Información para Spotify",
                    value="**Responde:** plan + correo/usuario + país/plataforma y método de pago\n\n**Planes disponibles:**\n• Individual 6m: $250\n• Individual 12m: $390\n• Duo 6m: $480\n• Duo 12m: $650",
                    inline=False
                )
            elif ticket_type == "youtube":
                embed.add_field(
                    name="▶️ Información para YouTube Premium",
                    value="**Responde:** meses + correo/usuario y método de pago\n\n**Planes disponibles:**\n• 6 meses: $300\n• 9 meses: $450\n• 12 meses: $500",
                    inline=False
                )
            elif ticket_type == "crunchyroll":
                embed.add_field(
                    name="🍥 Información para Crunchyroll",
                    value="**Responde:** plan + correo/usuario y método de pago\n\n**Planes disponibles:**\n• MegaFan 12m: $450\n• Individual 12m: $350\n• Individual 1m: $85",
                    inline=False
                )
            elif ticket_type == "robux":
                embed.add_field(
                    name="🧱 Información para Robux",
                    value="**Responde:** cantidad RBX + usuario Roblox y método de pago\n\n**Tarifa:** $0.165/RBX\n**Ejemplos:**\n• 1k RBX: $165\n• 5k RBX: $825\n• 10k RBX: $1,650\n\n**Requisito:** Unirte 15 días antes al grupo\n**Grupo:** https://www.roblox.com/share/g/42928445",
                    inline=False
                )
            elif ticket_type == "accesorios":
                embed.add_field(
                    name="🎨 Información para Accesorios Discord",
                    value="**Responde:** accesorio deseado y método de pago para cotizar\n\n**Disponible:**\n• Decoraciones\n• Banners\n• Themes por regalo\n• Desktop/Mobile",
                    inline=False
                )
            elif ticket_type == "otro":
                embed.add_field(
                    name="❓ Información General",
                    value="Por favor, describe tu consulta o problema específico.\n\n**Incluye:**\n• Descripción detallada\n• Método de pago preferido\n• Cualquier información adicional",
                    inline=False
                )
            elif ticket_type == "ayuda":
                embed.add_field(
                    name="🆘 Información para Ayuda",
                    value="**Responde:** describe tu problema o consulta\n\n**Incluye:**\n• Descripción detallada del problema\n• Pasos que ya intentaste\n• Capturas de pantalla si es necesario\n• Cualquier información adicional relevante",
                    inline=False
                )

            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
            
            # Crear vista de gestión de tickets (usar TicketManagementView para botones de gestión)
            from views.ticket_management_view import TicketManagementView
            management_view = TicketManagementView(ticket_id)
            
            # Enviar mensaje de bienvenida con botones de gestión
            try:
                welcome_message = await ticket_channel.send(embed=embed, view=management_view)
                log.info(f"Mensaje de bienvenida con botones de gestión enviado en ticket #{ticket_number}")
                
                # Hacer @user en el canal del ticket para notificar
                await ticket_channel.send(f"{user.mention} - Tu ticket ha sido creado. Un miembro del staff te atenderá pronto.")
                
            except Exception as e:
                log.error(f"Error enviando mensaje de bienvenida en ticket #{ticket_number}: {e}")
                # Enviar mensaje simple como último recurso
                await ticket_channel.send(f"🎫 **Ticket #{ticket_number} creado**\nHola {user.mention}! Un miembro del staff te atenderá pronto.")
            
            # Notificar al usuario (ctx puede ser Context o Interaction)
            try:
                if hasattr(ctx, 'send'):  # Es un Context
                    await ctx.send(
                        f"✅ ¡Ticket creado exitosamente!\n"
                        f"Tu canal privado: {ticket_channel.mention}\n"
                        f"Un miembro del staff te atenderá pronto."
                    )
                elif hasattr(ctx, 'followup'):  # Es un Interaction
                    await ctx.followup.send(
                        f"✅ ¡Ticket creado exitosamente!\n"
                        f"Tu canal privado: {ticket_channel.mention}\n"
                        f"Un miembro del staff te atenderá pronto.",
                        ephemeral=False
                    )
            except Exception as e:
                log.warning(f"No se pudo enviar notificación al usuario: {e}")
            
            # Log en canal de logs si existe
            if TICKETS_LOG_CHANNEL_ID:
                log_channel = guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = nextcord.Embed(
                        title="🎫 Nuevo Ticket Creado",
                        description=f"**Usuario:** {user.mention} ({user.id})\n"
                                   f"**Tipo:** {ticket_type.title()}\n"
                                   f"**Canal:** {ticket_channel.mention}\n"
                                   f"**Ticket #:** {ticket_number}",
                        color=0x00E5A8,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=log_embed)
            
            log.info(f"Ticket #{ticket_number} creado para {user.display_name} - Tipo: {ticket_type}")
            
        except Exception as e:
            # Manejar error según el tipo de contexto
            try:
                if hasattr(ctx, 'send'):  # Es un Context
                    await ctx.send("❌ Error creando el canal de ticket")
                elif hasattr(ctx, 'followup'):  # Es un Interaction
                    await ctx.followup.send("❌ Error creando el canal de ticket", ephemeral=True)
            except:
                pass
            log.error(f"Error creando ticket: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
    
    @commands.command(name="limpiar_canales_tickets")
    async def limpiar_canales_tickets(self, ctx):
        """Comando para eliminar todos los canales de tickets antiguos (solo staff)"""
        # Verificar permisos de staff
        if not is_admin(ctx.author):
            await ctx.send("❌ Solo owner/staff pueden usar este comando.")
            return
        
        try:
            deleted_count = 0
            error_count = 0
            
            # Buscar todos los canales que empiecen con "ticket-"
            for channel in ctx.guild.channels:
                if isinstance(channel, nextcord.TextChannel) and channel.name.startswith("ticket-"):
                    try:
                        await channel.delete(reason=f"Limpieza de canales de tickets por {ctx.author.name}")
                        deleted_count += 1
                        log.info(f"Canal de ticket eliminado: {channel.name} (ID: {channel.id})")
                    except Exception as e:
                        error_count += 1
                        log.error(f"Error eliminando canal {channel.name}: {e}")
            
            # Crear embed de resultado
            embed = nextcord.Embed(
                title="🧹 Limpieza de Canales de Tickets",
                description=f"**Canales eliminados:** {deleted_count}\n**Errores:** {error_count}",
                color=0x00E5A8,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Ejecutado por {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            log.info(f"Limpieza de canales completada: {deleted_count} eliminados, {error_count} errores")
            
        except Exception as e:
            await ctx.send("❌ Error al limpiar canales de tickets")
            log.error(f"Error en limpiar_canales_tickets: {e}")
    
    @commands.command(name="limpiar_tickets")
    async def limpiar_tickets(self, ctx):
        """Comando para limpiar todos los tickets (solo staff)"""
        # Verificar permisos de staff
        if not is_admin(ctx.author):
            await ctx.send("❌ Solo owner/staff pueden usar este comando.")
            return
        
        try:
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="🧹 Limpiar Tickets",
                description="⚠️ **ADVERTENCIA:** Esta acción eliminará TODOS los tickets del sistema.\n\n"
                           "**¿Estás seguro de que quieres continuar?**\n"
                           "Responde con `sí` o `si` para confirmar, o cualquier otra cosa para cancelar.",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="Esta acción no se puede deshacer")
            
            await ctx.send(embed=embed)
            
            # Esperar respuesta del usuario
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                if response.content.lower() in ['sí', 'si', 'yes', 'y']:
                    # Limpiar tickets
                    data = load_data()
                    tickets_count = len(data["tickets"])
                    
                    # Crear backup
                    import json
                    with open(f"data/bot_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                        json.dump(data, f, indent=2)
                    
                    # Limpiar datos
                    data["tickets"] = {}
                    data["ticket_counter"] = 0
                    save_data(data)
                    
                    # Embed de confirmación
                    success_embed = nextcord.Embed(
                        title="✅ Tickets Limpiados",
                        description=f"Se han eliminado **{tickets_count}** tickets del sistema.\n"
                                   f"Se ha creado un backup de seguridad.",
                        color=0x00FF00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    success_embed.add_field(
                        name="📊 Estadísticas",
                        value=f"• **Tickets eliminados:** {tickets_count}\n• **Contador reiniciado:** 0\n• **Backup creado:** ✅",
                        inline=False
                    )
                    success_embed.set_footer(text="Sistema de tickets reiniciado")
                    
                    await ctx.send(embed=success_embed)
                    
                    # Log en canal de logs si existe
                    if TICKETS_LOG_CHANNEL_ID:
                        log_channel = ctx.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                        if log_channel:
                            log_embed = nextcord.Embed(
                                title="🧹 Sistema de Tickets Limpiado",
                                description=f"**Ejecutado por:** {ctx.author.mention} ({ctx.author.id})\n"
                                           f"**Tickets eliminados:** {tickets_count}\n"
                                           f"**Canal:** {ctx.channel.mention}",
                                color=0xFFA500,
                                timestamp=datetime.now(timezone.utc)
                            )
                            await log_channel.send(embed=log_embed)
                    
                    log.info(f'Sistema de tickets limpiado por {ctx.author.id} - {tickets_count} tickets eliminados')
                    
                else:
                    await ctx.send("❌ Operación cancelada.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Tiempo de espera agotado. Operación cancelada.")
            
        except Exception as e:
            log.error(f'Error al limpiar tickets: {str(e)}')
            await ctx.send("❌ Hubo un error al limpiar los tickets. Por favor, inténtalo de nuevo.")

class SimpleTicketView(nextcord.ui.View):
    """Vista simplificada para selección de tipos de tickets"""
    
    def __init__(self, ticket_commands_instance=None):
        super().__init__(timeout=None)
        self.ticket_commands = ticket_commands_instance
        self._update_custom_ids()
    
    def _update_custom_ids(self):
        """Actualiza los custom_ids para evitar conflictos"""
        timestamp = str(int(datetime.now().timestamp()))
        for item in self.children:
            if hasattr(item, 'custom_id'):
                item.custom_id = f"{item.custom_id}_{timestamp}"
    
    @nextcord.ui.select(
        placeholder="🎫 Selecciona el tipo de servicio...",
        options=[
            nextcord.SelectOption(
                label="💬 Discord Nitro/Basic",
                value="discord",
                description="Suscripciones premium de Discord"
            ),
            nextcord.SelectOption(
                label="🎵 Spotify",
                value="spotify", 
                description="Individual y Duo"
            ),
            nextcord.SelectOption(
                label="▶️ YouTube Premium",
                value="youtube",
                description="Acceso sin anuncios"
            ),
            nextcord.SelectOption(
                label="🍥 Crunchyroll",
                value="crunchyroll",
                description="Anime y manga"
            ),
            nextcord.SelectOption(
                label="🧱 Robux",
                value="robux",
                description="Moneda virtual de Roblox"
            ),
            nextcord.SelectOption(
                label="🎨 Accesorios Discord",
                value="accesorios",
                description="Decoraciones y themes"
            ),
            nextcord.SelectOption(
                label="❓ Otro",
                value="otro",
                description="Consulta general"
            ),
            nextcord.SelectOption(
                label="🆘 Ayuda",
                value="ayuda",
                description="Soporte técnico"
            )
        ]
    )
    async def select_ticket_type(self, select: nextcord.ui.Select, interaction: nextcord.Interaction):
        """Maneja la selección del tipo de ticket"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            user = interaction.user
            guild = interaction.guild
            ticket_type = select.values[0]
            
            # Owner puede crear tickets sin límites
            is_owner = user.id == OWNER_DISCORD_ID
            
            # Verificar cooldown y rate limiting (excepto para owner)
            if not is_owner and self.ticket_commands:
                can_create, seconds_remaining = self.ticket_commands.rate_limiter.check_cooldown(user.id, OWNER_DISCORD_ID)
                if not can_create:
                    minutes = seconds_remaining // 60
                    seconds = seconds_remaining % 60
                    await interaction.followup.send(
                        f"⏰ Debes esperar {minutes}m {seconds}s antes de crear otro ticket",
                        ephemeral=True
                    )
                    return
            
            # Verificar si ya tiene un ticket abierto (excepto para owner)
            if not is_owner:
                open_ticket_id = find_open_ticket(guild, user.id)
                if open_ticket_id:
                    await interaction.followup.send(
                        f"❌ Ya tienes un ticket abierto ({open_ticket_id}). Por favor, espera a que se resuelva o contacta al staff.",
                        ephemeral=True
                    )
                    return
            
            # Actualizar tracking del usuario
            if self.ticket_commands:
                self.ticket_commands.rate_limiter.update_user_ticket_tracking(user.id)

            # Crear el ticket usando el sistema integrado
            await self.ticket_commands._create_ticket(guild, user, ticket_type, interaction)
            
        except Exception as e:
            await interaction.followup.send("❌ Error creando ticket", ephemeral=True)
            log.error(f"Error en select_ticket_type: {e}")
        finally:
            # Discord deja marcada la opción elegida y no manda evento si se repite: reiniciar el menú.
            try:
                await interaction.message.edit(view=self)
            except Exception as e:
                log.warning(f"No se pudo reiniciar el menú del panel: {e}")

def setup(bot: commands.Bot):
    """Setup del cog"""
    ticket_cog_instance = SimpleTicketCommands(bot)
    bot.add_cog(ticket_cog_instance)
    
    # Agregar evento para logear conversaciones en tickets
    @bot.event
    async def on_message(message):
        """Evento para logear mensajes en canales de tickets"""
        if message.author.bot:
            return
        if message.channel.name.startswith('ticket-'):
            try:
                data = load_data()
                for ticket_id, ticket in data["tickets"].items():
                    if str(ticket.get("channel_id")) == str(message.channel.id):
                        user_id = ticket["user_id"]
                        await ticket_cog_instance._log_conversation(
                            message.channel.id,
                            user_id,
                            message.content,
                            message.author.display_name,
                            "message"
                        )
                        break
            except Exception as e:
                log.error(f"Error logging ticket message: {e}")
