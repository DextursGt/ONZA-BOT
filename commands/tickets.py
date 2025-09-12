"""
Comandos relacionados con tickets
"""

import asyncio
from datetime import datetime, timezone
import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion, db_execute, db_query_one
from i18n import t, get_user_lang

class TicketCommands(commands.Cog):
    """Comandos relacionados con tickets"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
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
            title=f"🎫 Soporte {BRAND_NAME}",
            description="Elige un servicio para abrir tu ticket privado.\n\n**Horario de atención:** 24/7\n**Tiempo de respuesta:** < 50 minutos",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="📋 **Servicios Disponibles**",
            value="• **Compras:** Haz tu pedido\n• **Verificación:** Confirmar tu compra\n• **Garantía:** Reclamar garantía de producto\n• **Otro:** Consultas generales",
            inline=False
        )
        
        embed.add_field(
            name="⚡ **Respuesta Rápida**",
            value="Nuestro equipo te responderá en menos de 50 minutos.",
            inline=False
        )
        
        embed.set_footer(text=f"{BRAND_NAME} • Soporte 24/7")
        
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
        placeholder="🎫 Selecciona el tipo de ticket...",
        options=[
            nextcord.SelectOption(
                label="🛒 Compras",
                description="Hacer un pedido o consulta sobre productos",
                value="compras"
            ),
            nextcord.SelectOption(
                label="✅ Verificación",
                description="Confirmar tu compra o verificar estado",
                value="verificacion"
            ),
            nextcord.SelectOption(
                label="🛡️ Garantía",
                description="Reclamar garantía de producto",
                value="garantia"
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
            if ticket_type == "compras":
                embed.add_field(
                    name="🛒 Información para Compras",
                    value="Por favor, incluye:\n• Producto que deseas\n• Cantidad\n• Método de pago preferido",
                    inline=False
                )
            elif ticket_type == "verificacion":
                embed.add_field(
                    name="✅ Información para Verificación",
                    value="Por favor, incluye:\n• Número de orden\n• Fecha de compra\n• Método de pago usado",
                    inline=False
                )
            elif ticket_type == "garantia":
                embed.add_field(
                    name="🛡️ Información para Garantía",
                    value="Por favor, incluye:\n• Producto con garantía\n• Fecha de compra\n• Descripción del problema",
                    inline=False
                )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
            
            # Vista de control para el ticket
            control_view = TicketControlView(user.id)
            
            await ticket_channel.send(embed=embed, view=control_view)
            
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