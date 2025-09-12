"""
Comandos relacionados con tickets
"""

import asyncio
from datetime import datetime, timezone, timedelta
import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion, db_execute, db_query_one
from i18n import t, get_user_lang

class TicketCommands(commands.Cog):
    """Comandos relacionados con tickets"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Sistema de cooldown para prevenir spam
        self.user_cooldowns = {}  # {user_id: last_ticket_time}
        self.ticket_cooldown = 300  # 5 minutos entre tickets
        self.max_tickets_per_hour = 3  # Máximo 3 tickets por hora
        self.user_ticket_counts = {}  # {user_id: [timestamps]}
    
    def _check_cooldown(self, user_id: int) -> tuple[bool, int]:
        """Verificar si el usuario está en cooldown
        Returns: (can_create_ticket, seconds_remaining)
        """
        current_time = datetime.now(timezone.utc).timestamp()
        
        # Verificar cooldown básico (5 minutos)
        if user_id in self.user_cooldowns:
            time_since_last = current_time - self.user_cooldowns[user_id]
            if time_since_last < self.ticket_cooldown:
                return False, int(self.ticket_cooldown - time_since_last)
        
        # Verificar rate limiting (máximo 3 tickets por hora)
        if user_id in self.user_ticket_counts:
            hour_ago = current_time - 3600  # 1 hora
            recent_tickets = [t for t in self.user_ticket_counts[user_id] if t > hour_ago]
            
            if len(recent_tickets) >= self.max_tickets_per_hour:
                # Calcular cuándo puede crear el siguiente ticket
                oldest_ticket = min(recent_tickets)
                next_available = oldest_ticket + 3600
                return False, int(next_available - current_time)
        
        return True, 0
    
    def _update_user_ticket_tracking(self, user_id: int):
        """Actualizar el tracking de tickets del usuario"""
        current_time = datetime.now(timezone.utc).timestamp()
        
        # Actualizar cooldown
        self.user_cooldowns[user_id] = current_time
        
        # Actualizar contador de tickets
        if user_id not in self.user_ticket_counts:
            self.user_ticket_counts[user_id] = []
        
        self.user_ticket_counts[user_id].append(current_time)
        
        # Limpiar tickets antiguos (más de 1 hora)
        hour_ago = current_time - 3600
        self.user_ticket_counts[user_id] = [t for t in self.user_ticket_counts[user_id] if t > hour_ago]
    
    @nextcord.slash_command(name="panel", description="Publica el panel de tickets (solo staff)")
    async def panel(self, interaction: nextcord.Interaction, canal: nextcord.TextChannel = None):
        """Publicar panel de tickets con botones interactivos"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        # Usar canal especificado o canal actual
        target_channel = canal or interaction.channel
        
        # Crear embed del panel
        embed = nextcord.Embed(
            title=f"🎫 Servicios {BRAND_NAME}",
            description="Elige un servicio para abrir tu ticket privado.\n\n**Horario de atención:** 10:00 AM - 10:00 PM\n**Tiempo de respuesta:** < 50 minutos",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="💬 **Discord Nitro / Basic**",
            value="",
            inline=False
        )
        
        embed.add_field(
            name="🎵 **Spotify (Individual/Duo)**",
            value="",
            inline=False
        )
        
        embed.add_field(
            name="▶️ **YouTube Premium**",
            value="",
            inline=False
        )
        
        embed.add_field(
            name="🍥 **Crunchyroll**",
            value="",
            inline=False
        )
        
        embed.add_field(
            name="🧱 **Robux por grupo**",
            value="",
            inline=False
        )
        
        embed.add_field(
            name="🎨 **Accesorios de Discord**",
            value="",
            inline=False
        )
        
        embed.set_footer(text=f"{BRAND_NAME} • Soporte 10:00 AM - 10:00 PM")
        
        # Crear vista con botones
        view = TicketView()
        
        # Enviar panel
        await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Panel de tickets publicado en {target_channel.mention}", ephemeral=True)
        
        # Log de la acción
        await log_accion("Panel de Tickets", interaction.user.display_name, f"Canal: {target_channel.name}")
    
    @nextcord.slash_command(name="limpiar_tickets", description="Limpiar tickets cerrados (solo staff)")
    async def limpiar_tickets(self, interaction: nextcord.Interaction):
        """Limpiar tickets cerrados automáticamente"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Buscar categoría de tickets
            tickets_category = None
            for category in interaction.guild.categories:
                if TICKETS_CATEGORY_NAME.lower() in category.name.lower():
                    tickets_category = category
                    break
            
            if not tickets_category:
                await interaction.followup.send("❌ No se encontró la categoría de tickets.", ephemeral=True)
                return
            
            # Buscar canales cerrados
            closed_channels = []
            for channel in tickets_category.channels:
                if isinstance(channel, nextcord.TextChannel):
                    # Verificar si es un canal de ticket cerrado
                    if "cerrado" in channel.name.lower() or "closed" in channel.name.lower():
                        closed_channels.append(channel)
            
            if not closed_channels:
                await interaction.followup.send("✅ No hay tickets cerrados para limpiar.", ephemeral=True)
                return
            
            # Eliminar canales
            deleted_count = 0
            for channel in closed_channels:
                try:
                    await channel.delete()
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Error eliminando canal {channel.name}: {e}")
            
            # Crear embed de resumen
            embed = nextcord.Embed(
                title="🧹 Limpieza de Tickets Completada",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📊 **Resumen**",
                value=f"• **Canales encontrados:** {len(closed_channels)}\n• **Canales eliminados:** {deleted_count}\n• **Errores:** {len(closed_channels) - deleted_count}",
                inline=False
            )
            
            embed.set_footer(text="ONZA Bot • Sistema de Limpieza")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            await log_accion("Limpieza de Tickets", interaction.user.display_name, f"Eliminados: {deleted_count}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error limpiando tickets: {str(e)}", ephemeral=True)
            log.error(f"Error en limpiar_tickets: {e}")
    
    @nextcord.slash_command(name="estado_tickets", description="Ver estado de tickets (solo staff)")
    async def estado_tickets(self, interaction: nextcord.Interaction):
        """Ver estado actual de tickets"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Obtener estadísticas de tickets
            open_tickets = await db_query_one("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
            closed_tickets = await db_query_one("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
            completed_tickets = await db_query_one("SELECT COUNT(*) FROM tickets WHERE status = 'completed'")
            
            # Obtener tickets recientes
            recent_tickets = await db_query_one(
                "SELECT COUNT(*) FROM tickets WHERE created_at > ?",
                (datetime.now(timezone.utc).timestamp() - 3600,)  # Última hora
            )
            
            # Crear embed de estado
            embed = nextcord.Embed(
                title="📊 Estado del Sistema de Tickets",
                color=0x00E5A8,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="🎫 **Tickets Activos**",
                value=f"• **Abiertos:** {open_tickets[0] if open_tickets else 0}\n"
                      f"• **Completados:** {completed_tickets[0] if completed_tickets else 0}\n"
                      f"• **Cerrados:** {closed_tickets[0] if closed_tickets else 0}",
                inline=True
            )
            
            embed.add_field(
                name="⏰ **Actividad Reciente**",
                value=f"• **Última hora:** {recent_tickets[0] if recent_tickets else 0} tickets\n"
                      f"• **Cooldown activo:** {len(self.user_cooldowns)} usuarios\n"
                      f"• **Rate limiting:** {len(self.user_ticket_counts)} usuarios",
                inline=True
            )
            
            # Información del sistema
            embed.add_field(
                name="⚙️ **Configuración**",
                value=f"• **Cooldown:** {self.ticket_cooldown}s\n"
                      f"• **Límite por hora:** {self.max_tickets_per_hour}\n"
                      f"• **Categoría:** {TICKETS_CATEGORY_NAME}",
                inline=False
            )
            
            embed.set_footer(text="ONZA Bot • Sistema de Tickets")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error obteniendo estado: {str(e)}", ephemeral=True)
            log.error(f"Error en estado_tickets: {e}")
    
    @nextcord.slash_command(name="diagnosticar_ticket", description="Diagnosticar problemas con un ticket específico (solo staff)")
    async def diagnosticar_ticket(self, interaction: nextcord.Interaction, canal: nextcord.TextChannel = None):
        """Diagnosticar problemas con un ticket específico"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Usar canal especificado o canal actual
            target_channel = canal or interaction.channel
            
            # Verificar si es un canal de ticket
            if not target_channel.name.startswith('ticket-'):
                await interaction.followup.send("❌ Este comando solo funciona en canales de ticket.", ephemeral=True)
                return
            
            # Obtener información del ticket de la base de datos
            ticket_info = await db_query_one(
                "SELECT * FROM tickets WHERE discord_channel_id = ?",
                (target_channel.id,)
            )
            
            if not ticket_info:
                await interaction.followup.send("❌ No se encontró información del ticket en la base de datos.", ephemeral=True)
                return
            
            # Obtener información del canal
            channel_info = {
                'id': target_channel.id,
                'name': target_channel.name,
                'created_at': target_channel.created_at,
                'permissions': len(target_channel.overwrites),
                'category': target_channel.category.name if target_channel.category else "Sin categoría"
            }
            
            # Obtener mensajes recientes
            recent_messages = []
            async for message in target_channel.history(limit=5):
                recent_messages.append({
                    'author': message.author.display_name,
                    'content': message.content[:50] + "..." if len(message.content) > 50 else message.content,
                    'embeds': len(message.embeds),
                    'components': len(message.components)
                })
            
            # Crear embed de diagnóstico
            embed = nextcord.Embed(
                title="🔍 Diagnóstico de Ticket",
                description=f"**Canal:** {target_channel.mention}",
                color=0x0099FF,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(
                name="📊 **Información de Base de Datos**",
                value=f"• **ID:** {ticket_info[0]}\n"
                      f"• **Usuario:** <@{ticket_info[1]}>\n"
                      f"• **Estado:** {ticket_info[2]}\n"
                      f"• **Creado:** <t:{int(ticket_info[3])}:F>",
                inline=True
            )
            
            embed.add_field(
                name="🔧 **Información del Canal**",
                value=f"• **Nombre:** {channel_info['name']}\n"
                      f"• **Categoría:** {channel_info['category']}\n"
                      f"• **Permisos:** {channel_info['permissions']}\n"
                      f"• **Creado:** <t:{int(channel_info['created_at'].timestamp())}:F>",
                inline=True
            )
            
            # Información de mensajes recientes
            if recent_messages:
                messages_text = "\n".join([
                    f"• **{msg['author']}:** {msg['content']} (Embeds: {msg['embeds']}, Components: {msg['components']})"
                    for msg in recent_messages[:3]
                ])
                embed.add_field(
                    name="💬 **Mensajes Recientes**",
                    value=messages_text,
                    inline=False
                )
            
            # Verificar problemas comunes
            issues = []
            if not recent_messages:
                issues.append("⚠️ No hay mensajes en el canal")
            elif not any(msg['components'] > 0 for msg in recent_messages):
                issues.append("⚠️ No se detectaron botones de control")
            
            if issues:
                embed.add_field(
                    name="🚨 **Problemas Detectados**",
                    value="\n".join(issues),
                    inline=False
                )
            
            embed.set_footer(text="ONZA Bot • Diagnóstico de Tickets")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error en diagnóstico: {str(e)}", ephemeral=True)
            log.error(f"Error en diagnosticar_ticket: {e}")
    
    @nextcord.slash_command(name="cerrar_mi_ticket", description="Cerrar tu ticket (solo si está completado)")
    async def cerrar_mi_ticket(self, interaction: nextcord.Interaction):
        """Permitir al usuario cerrar su ticket si está completado"""
        try:
            # Verificar que esté en un canal de ticket
            if not interaction.channel.name.startswith('ticket-'):
                await interaction.response.send_message("❌ Este comando solo funciona en canales de ticket.", ephemeral=True)
                return
            
            # Obtener información del ticket
            ticket_info = await db_query_one(
                "SELECT user_id, status FROM tickets WHERE discord_channel_id = ?",
                (interaction.channel.id,)
            )
            
            if not ticket_info:
                await interaction.response.send_message("❌ No se encontró información del ticket.", ephemeral=True)
                return
            
            user_id, status = ticket_info
            
            # Verificar que sea el propietario del ticket
            if interaction.user.id != user_id:
                await interaction.response.send_message("❌ Solo el propietario del ticket puede cerrarlo.", ephemeral=True)
                return
            
            # Verificar que el ticket esté completado
            if status != 'completed':
                await interaction.response.send_message("❌ Solo puedes cerrar tickets que hayan sido completados por el staff.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Actualizar estado en base de datos
            await db_execute(
                "UPDATE tickets SET status = 'closed', closed_at = ? WHERE discord_channel_id = ?",
                (datetime.now(timezone.utc).timestamp(), interaction.channel.id)
            )
            
            # Crear embed de cierre
            embed = nextcord.Embed(
                title="🔒 Ticket Cerrado por Usuario",
                description=f"Este ticket ha sido cerrado por {interaction.user.mention}.\n"
                           f"El canal será eliminado en 10 segundos.",
                color=0xFF6B6B,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.followup.send(embed=embed)
            
            # Log de cierre
            if TICKETS_LOG_CHANNEL_ID:
                log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = nextcord.Embed(
                        title="🔒 Ticket Cerrado por Usuario",
                        description=f"**Ticket:** {interaction.channel.mention}\n"
                                   f"**Cerrado por:** {interaction.user.mention}\n"
                                   f"**Usuario:** <@{user_id}>",
                        color=0xFF6B6B,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=log_embed)
            
            # Esperar y eliminar canal
            await asyncio.sleep(10)
            await interaction.channel.delete()
            
        except Exception as e:
            await interaction.followup.send("❌ Error cerrando ticket", ephemeral=True)
            log.error(f"Error en cerrar_mi_ticket: {e}")

class TicketView(nextcord.ui.View):
    """Vista para el panel de tickets"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @nextcord.ui.select(
        placeholder="🎫 Selecciona el servicio que necesitas...",
        options=[
            nextcord.SelectOption(
                label="💬 Discord Nitro/Basic",
                description="Nitro 1a $649 · 1m $90 · Basic 1a $349 · 1m $40",
                value="discord"
            ),
            nextcord.SelectOption(
                label="🎵 Spotify",
                description="Ind 6m $250 · 12m $390 · Duo 6m $480 · 12m $650",
                value="spotify"
            ),
            nextcord.SelectOption(
                label="▶️ YouTube Premium",
                description="6m $300 · 9m $450 · 12m $500",
                value="youtube"
            ),
            nextcord.SelectOption(
                label="🍥 Crunchyroll",
                description="MegaFan 12m $450 · Individual 12m $350 · 1m $85",
                value="crunchyroll"
            ),
            nextcord.SelectOption(
                label="🧱 Robux",
                description="Tarifa $0.165/RBX · 1k $165 · 5k $825 · 10k $1,650",
                value="robux"
            ),
            nextcord.SelectOption(
                label="🎨 Accesorios Discord",
                description="Decoraciones, banners, themes por regalo",
                value="accesorios"
            ),
            nextcord.SelectOption(
                label="❓ Otro",
                description="Consultas generales o soporte técnico",
                value="otro"
            )
        ]
    )
    async def select_ticket_type(self, select: nextcord.ui.Select, interaction: nextcord.Interaction):
        """Manejar selección de tipo de ticket"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            ticket_type = select.values[0]
            user = interaction.user
            guild = interaction.guild
            
            # Verificar cooldown y rate limiting
            can_create, seconds_remaining = self._check_cooldown(user.id)
            if not can_create:
                minutes = seconds_remaining // 60
                seconds = seconds_remaining % 60
                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                
                await interaction.followup.send(
                    f"⏰ **Cooldown activo**\n"
                    f"Debes esperar **{time_str}** antes de crear otro ticket.\n\n"
                    f"**Límites:**\n"
                    f"• 1 ticket cada 5 minutos\n"
                    f"• Máximo 3 tickets por hora",
                    ephemeral=True
                )
                return
            
            # Verificar si ya tiene un ticket abierto
            existing_ticket = await db_query_one(
                "SELECT discord_channel_id FROM tickets WHERE user_id = ? AND status = 'open'",
                (user.id,)
            )
            
            if existing_ticket:
                channel = guild.get_channel(existing_ticket[0])
                if channel:
                    await interaction.followup.send(
                        f"❌ Ya tienes un ticket abierto: {channel.mention}\n"
                        f"Por favor, usa ese canal para continuar con tu consulta.",
                        ephemeral=True
                    )
                    return
            
            # Actualizar tracking del usuario
            self._update_user_ticket_tracking(user.id)
            
            # Crear el ticket
            await self._create_ticket(guild, user, ticket_type, interaction)
            
        except Exception as e:
            await interaction.followup.send("❌ Error creando ticket", ephemeral=True)
            log.error(f"Error en select_ticket_type: {e}")
    
    async def _create_ticket(self, guild: nextcord.Guild, user: nextcord.Member, ticket_type: str, interaction: nextcord.Interaction):
        """Crear un nuevo ticket"""
        try:
            # Obtener o crear categoría de tickets
            category = None
            for cat in guild.categories:
                if cat.name.lower() == TICKETS_CATEGORY_NAME.lower():
                    category = cat
                    break
            
            if not category:
                category = await guild.create_category(TICKETS_CATEGORY_NAME)
            
            # Crear canal de ticket
            ticket_number = await self._get_next_ticket_number()
            channel_name = f"ticket-{ticket_number}-{user.display_name.lower().replace(' ', '-')}"
            
            # Permisos del canal
            overwrites = {
                guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Agregar roles de staff si existen
            if STAFF_ROLE_ID:
                staff_role = guild.get_role(STAFF_ROLE_ID)
                if staff_role:
                    overwrites[staff_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            if SUPPORT_ROLE_ID and SUPPORT_ROLE_ID != STAFF_ROLE_ID:
                support_role = guild.get_role(SUPPORT_ROLE_ID)
                if support_role:
                    overwrites[support_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            # Crear el canal
            ticket_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_number} - {user.display_name} - {ticket_type.title()}"
            )
            
            # Registrar en la base de datos
            await db_execute(
                """INSERT INTO tickets (discord_channel_id, user_id, status, created_at) 
                   VALUES (?, ?, 'open', ?)""",
                (ticket_channel.id, user.id, datetime.now(timezone.utc).timestamp())
            )
            
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
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
            
            # Vista de control para el ticket
            control_view = TicketControlView(user.id)
            
            # Enviar mensaje de bienvenida con manejo de errores mejorado
            try:
                welcome_message = await ticket_channel.send(embed=embed, view=control_view)
                log.info(f"Mensaje de bienvenida enviado en ticket #{ticket_number}")
            except Exception as e:
                log.error(f"Error enviando mensaje de bienvenida en ticket #{ticket_number}: {e}")
                # Intentar enviar sin la vista si hay problemas
                try:
                    await ticket_channel.send(embed=embed)
                    log.info(f"Mensaje de bienvenida enviado sin vista en ticket #{ticket_number}")
                except Exception as e2:
                    log.error(f"Error crítico enviando mensaje en ticket #{ticket_number}: {e2}")
                    # Enviar mensaje simple como último recurso
                    await ticket_channel.send(f"🎫 **Ticket #{ticket_number} creado**\nHola {user.mention}! Un miembro del staff te atenderá pronto.")
            
            # Notificar al usuario
            await interaction.followup.send(
                f"✅ ¡Ticket creado exitosamente!\n"
                f"Tu canal privado: {ticket_channel.mention}\n"
                f"Un miembro del staff te atenderá pronto.",
                ephemeral=True
            )
            
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
            await interaction.followup.send("❌ Error creando el canal de ticket", ephemeral=True)
            log.error(f"Error creando ticket: {e}")
    
    async def _get_next_ticket_number(self) -> int:
        """Obtener el siguiente número de ticket"""
        try:
            result = await db_query_one("SELECT MAX(id) FROM tickets")
            return (result[0] if result and result[0] else 0) + 1
        except Exception:
            return 1

class TicketControlView(nextcord.ui.View):
    """Vista de control para tickets con botones específicos por rol"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        # Asegurar que los custom_id sean únicos
        self._update_custom_ids()
    
    def _update_custom_ids(self):
        """Actualizar custom_ids para evitar conflictos"""
        timestamp = int(datetime.now(timezone.utc).timestamp())
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id:
                item.custom_id = f"{item.custom_id}_{self.user_id}_{timestamp}"
    
    @nextcord.ui.button(label="🔒 Cerrar Ticket", style=nextcord.ButtonStyle.danger, custom_id="close_ticket", row=0)
    async def close_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Cerrar el ticket (solo moderadores)"""
        try:
            # Verificar que sea staff
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede cerrar tickets.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Actualizar estado en base de datos
            await db_execute(
                "UPDATE tickets SET status = 'closed', closed_at = ?, assigned_to = ? WHERE discord_channel_id = ?",
                (datetime.now(timezone.utc).timestamp(), interaction.user.id, interaction.channel.id)
            )
            
            # Crear embed de cierre
            embed = nextcord.Embed(
                title="🔒 Ticket Cerrado",
                description=f"Este ticket ha sido cerrado por {interaction.user.mention}.\n"
                           f"El canal será eliminado en 10 segundos.",
                color=0xFF6B6B,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.followup.send(embed=embed)
            
            # Log de cierre
            if TICKETS_LOG_CHANNEL_ID:
                guild = interaction.guild
                log_channel = guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = nextcord.Embed(
                        title="🔒 Ticket Cerrado",
                        description=f"**Ticket:** {interaction.channel.mention}\n"
                                   f"**Cerrado por:** {interaction.user.mention}\n"
                                   f"**Usuario:** <@{self.user_id}>",
                        color=0xFF6B6B,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=log_embed)
            
            # Esperar y eliminar canal
            await asyncio.sleep(10)
            await interaction.channel.delete()
            
        except Exception as e:
            await interaction.followup.send("❌ Error cerrando ticket", ephemeral=True)
            log.error(f"Error cerrando ticket: {e}")
    
    @nextcord.ui.button(label="📋 Más Información", style=nextcord.ButtonStyle.secondary, custom_id="more_info", row=0)
    async def more_info(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Solicitar más información (solo moderadores)"""
        try:
            # Verificar que sea staff
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este botón.", ephemeral=True)
                return
            
            # Crear modal para solicitar información
            modal = MoreInfoModal()
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            await interaction.response.send_message("❌ Error solicitando información", ephemeral=True)
            log.error(f"Error en more_info: {e}")
    
    @nextcord.ui.button(label="✅ Completado", style=nextcord.ButtonStyle.success, custom_id="complete_ticket", row=0)
    async def complete_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Marcar ticket como completado (solo moderadores)"""
        try:
            # Verificar que sea staff
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede completar tickets.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Actualizar estado en base de datos
            await db_execute(
                "UPDATE tickets SET status = 'completed', assigned_to = ? WHERE discord_channel_id = ?",
                (interaction.user.id, interaction.channel.id)
            )
            
            # Crear embed de completado
            embed = nextcord.Embed(
                title="✅ Ticket Completado",
                description=f"Este ticket ha sido marcado como completado por {interaction.user.mention}.\n"
                           f"El usuario puede cerrarlo cuando esté listo.",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.followup.send(embed=embed)
            
            # Notificar al usuario
            user = interaction.guild.get_member(self.user_id)
            if user:
                try:
                    dm_embed = nextcord.Embed(
                        title="✅ Ticket Completado",
                        description=f"Tu ticket en {interaction.guild.name} ha sido completado.\n"
                                   f"Puedes cerrarlo cuando estés listo usando el botón 'Cerrar Ticket'.",
                        color=0x00FF00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await user.send(embed=dm_embed)
                except:
                    pass  # Usuario tiene DMs deshabilitados
            
            # Log de completado
            if TICKETS_LOG_CHANNEL_ID:
                log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = nextcord.Embed(
                        title="✅ Ticket Completado",
                        description=f"**Ticket:** {interaction.channel.mention}\n"
                                   f"**Completado por:** {interaction.user.mention}\n"
                                   f"**Usuario:** <@{self.user_id}>",
                        color=0x00FF00,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=log_embed)
            
        except Exception as e:
            await interaction.followup.send("❌ Error completando ticket", ephemeral=True)
            log.error(f"Error completando ticket: {e}")
    
    @nextcord.ui.button(label="📈 Escalar", style=nextcord.ButtonStyle.primary, custom_id="escalate_ticket", row=1)
    async def escalate_ticket(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Escalar ticket (solo usuarios)"""
        try:
            # Verificar que sea el propietario del ticket
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Solo el propietario del ticket puede escalarlo.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            # Actualizar estado en base de datos
            await db_execute(
                "UPDATE tickets SET escalated = 1, last_action_at = ? WHERE discord_channel_id = ?",
                (datetime.now(timezone.utc).timestamp(), interaction.channel.id)
            )
            
            # Crear embed de escalación
            embed = nextcord.Embed(
                title="📈 Ticket Escalado",
                description=f"Este ticket ha sido escalado por {interaction.user.mention}.\n"
                           f"Un supervisor será notificado para revisar el caso.",
                color=0xFFA500,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.followup.send(embed=embed)
            
            # Notificar a supervisores (staff con rol más alto)
            if STAFF_ROLE_ID:
                staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
                if staff_role:
                    notification_embed = nextcord.Embed(
                        title="🚨 Ticket Escalado",
                        description=f"**Ticket:** {interaction.channel.mention}\n"
                                   f"**Usuario:** {interaction.user.mention}\n"
                                   f"**Motivo:** Escalación solicitada por el usuario",
                        color=0xFFA500,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await interaction.channel.send(f"{staff_role.mention}", embed=notification_embed)
            
            # Log de escalación
            if TICKETS_LOG_CHANNEL_ID:
                log_channel = interaction.guild.get_channel(TICKETS_LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = nextcord.Embed(
                        title="📈 Ticket Escalado",
                        description=f"**Ticket:** {interaction.channel.mention}\n"
                                   f"**Escalado por:** {interaction.user.mention}\n"
                                   f"**Usuario:** <@{self.user_id}>",
                        color=0xFFA500,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=log_embed)
            
        except Exception as e:
            await interaction.followup.send("❌ Error escalando ticket", ephemeral=True)
            log.error(f"Error escalando ticket: {e}")

class MoreInfoModal(nextcord.ui.Modal):
    """Modal para solicitar más información"""
    
    def __init__(self):
        super().__init__(title="Solicitar Más Información", timeout=300)
        
        self.info_input = nextcord.ui.TextInput(
            label="Información solicitada",
            placeholder="Describe qué información adicional necesitas del usuario...",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.info_input)
    
    async def callback(self, interaction: nextcord.Interaction):
        """Manejar el envío del modal"""
        try:
            await interaction.response.defer()
            
            # Crear embed con la información solicitada
            embed = nextcord.Embed(
                title="📋 Información Adicional Solicitada",
                description=f"**Solicitado por:** {interaction.user.mention}\n\n"
                           f"**Información requerida:**\n{self.info_input.value}",
                color=0x0099FF,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send("❌ Error enviando solicitud", ephemeral=True)
            log.error(f"Error en MoreInfoModal: {e}")