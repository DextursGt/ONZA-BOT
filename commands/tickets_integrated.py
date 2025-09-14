import nextcord
from nextcord.ext import commands
from nextcord import app_commands
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import uuid
import os

# Importar configuraciones y utilidades
from config_new import (
    TICKET_CHANNEL_ID, OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID,
    TICKETS_CATEGORY_NAME, TICKETS_LOG_CHANNEL_ID, BRAND_NAME
)
from data_manager_new import load_data, save_data, get_next_ticket_id
from utils_new import check_user_permissions, handle_interaction_response, logger
from views.enhanced_ticket_view import EnhancedTicketView
from views.ticket_management_view import TicketManagementView

# Configurar logging
log = logging.getLogger(__name__)

class IntegratedTicketCommands(commands.Cog):
    """Sistema de tickets integrado que combina funcionalidades de ambos bots"""
    
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}  # Para controlar spam
        self.user_ticket_counts = {}  # Para rate limiting
        
    def _check_cooldown(self, user_id: int) -> tuple[bool, int]:
        """Verifica si el usuario está en cooldown o ha alcanzado el límite de tickets"""
        current_time = datetime.now(timezone.utc)
        
        # Verificar cooldown (5 minutos entre tickets)
        if user_id in self.user_cooldowns:
            last_ticket_time = self.user_cooldowns[user_id]
            time_diff = (current_time - last_ticket_time).total_seconds()
            if time_diff < 300:  # 5 minutos
                remaining = 300 - int(time_diff)
                return False, remaining
        
        # Verificar rate limiting (máximo 3 tickets por hora)
        if user_id in self.user_ticket_counts:
            ticket_times = self.user_ticket_counts[user_id]
            # Filtrar tickets de la última hora
            recent_tickets = [
                t for t in ticket_times 
                if (current_time - t).total_seconds() < 3600
            ]
            if len(recent_tickets) >= 3:
                oldest_ticket = min(recent_tickets)
                remaining = 3600 - int((current_time - oldest_ticket).total_seconds())
                return False, remaining
        
        return True, 0
    
    def _update_user_ticket_tracking(self, user_id: int):
        """Actualiza el tracking de tickets del usuario"""
        current_time = datetime.now(timezone.utc)
        
        # Actualizar cooldown
        self.user_cooldowns[user_id] = current_time
        
        # Actualizar conteo de tickets
        if user_id not in self.user_ticket_counts:
            self.user_ticket_counts[user_id] = []
        self.user_ticket_counts[user_id].append(current_time)
        
        # Limpiar tickets antiguos (más de 1 hora)
        self.user_ticket_counts[user_id] = [
            t for t in self.user_ticket_counts[user_id]
            if (current_time - t).total_seconds() < 3600
        ]
    
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
    
    @app_commands.command(name="panel", description="Muestra el panel de tickets con servicios disponibles")
    async def panel(self, interaction: nextcord.Interaction, canal: nextcord.TextChannel = None):
        """Comando para mostrar el panel de tickets"""
        try:
            # Usar el canal especificado o el canal actual
            target_channel = canal or interaction.channel
            
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
            view = IntegratedTicketView(self)
            
            # Enviar mensaje
            await target_channel.send(embed=embed, view=view)
            
            # Confirmar al usuario
            await interaction.response.send_message(
                f"✅ Panel de tickets enviado a {target_channel.mention}",
                ephemeral=True
            )
            
            log.info(f"Panel de tickets enviado por {interaction.user.display_name} en {target_channel.name}")
            
        except Exception as e:
            await interaction.response.send_message("❌ Error al enviar el panel de tickets", ephemeral=True)
            log.error(f"Error en panel: {e}")
    
    @app_commands.command(name="ticket", description="Crear un ticket directamente")
    async def ticket(self, interaction: nextcord.Interaction):
        """Comando directo para crear tickets"""
        try:
            # Verificar cooldown y rate limiting
            can_create, seconds_remaining = self._check_cooldown(interaction.user.id)
            if not can_create:
                minutes = seconds_remaining // 60
                seconds = seconds_remaining % 60
                await interaction.response.send_message(
                    f"⏰ Debes esperar {minutes}m {seconds}s antes de crear otro ticket",
                    ephemeral=True
                )
                return
            
            # Verificar si ya tiene un ticket abierto
            data = load_data()
            user_id = str(interaction.user.id)
            has_open_ticket = False
            
            for ticket_id, ticket in data["tickets"].items():
                if (ticket["user_id"] == user_id and 
                    ticket["status"] == "abierto" and 
                    ticket.get("estado_detallado") not in ["cerrado_por_owner", "cerrado"]):
                    has_open_ticket = True
                    break
            
            if has_open_ticket:
                await interaction.response.send_message(
                    "❌ Ya tienes un ticket abierto. Por favor, espera a que se resuelva.",
                    ephemeral=True
                )
                return
            
            # Crear vista de selección de servicios
            view = IntegratedTicketView(self)
            embed = nextcord.Embed(
                title="🎫 Crear Ticket",
                description="Selecciona el tipo de servicio que necesitas:",
                color=0x00E5A8
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message("❌ Error al crear ticket", ephemeral=True)
            log.error(f"Error en ticket: {e}")
    
    @app_commands.command(name="cerrar_mi_ticket", description="Cierra tu ticket actual")
    async def cerrar_mi_ticket(self, interaction: nextcord.Interaction):
        """Permite al usuario cerrar su propio ticket"""
        try:
            # Verificar si está en un canal de ticket
            if not interaction.channel.name.startswith('ticket-'):
                await interaction.response.send_message(
                    "❌ Este comando solo funciona en canales de tickets",
                    ephemeral=True
                )
                return
            
            # Buscar el ticket en la base de datos
            data = load_data()
            ticket_found = None
            
            for ticket_id, ticket in data["tickets"].items():
                if str(ticket.get("channel_id")) == str(interaction.channel.id):
                    ticket_found = ticket_id
                    break
            
            if not ticket_found:
                await interaction.response.send_message(
                    "❌ No se encontró información del ticket",
                    ephemeral=True
                )
                return
            
            # Verificar que el usuario es el propietario del ticket
            if str(data["tickets"][ticket_found]["user_id"]) != str(interaction.user.id):
                await interaction.response.send_message(
                    "❌ Solo el propietario del ticket puede cerrarlo",
                    ephemeral=True
                )
                return
            
            # Actualizar estado del ticket
            data["tickets"][ticket_found]["status"] = "cerrado"
            data["tickets"][ticket_found]["estado_detallado"] = "cerrado_por_usuario"
            data["tickets"][ticket_found]["closed_by"] = str(interaction.user.id)
            data["tickets"][ticket_found]["closed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Agregar al historial
            data["tickets"][ticket_found]["historial"].append({
                "estado": "cerrado",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detalles": f"Ticket cerrado por el usuario {interaction.user.display_name}"
            })
            
            save_data(data)
            
            # Enviar mensaje de confirmación
            embed = nextcord.Embed(
                title="🔒 Ticket Cerrado",
                description="Tu ticket ha sido cerrado. El canal será eliminado en 10 segundos.",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Esperar y eliminar el canal
            await asyncio.sleep(10)
            await interaction.channel.delete()
            
        except Exception as e:
            await interaction.response.send_message("❌ Error cerrando ticket", ephemeral=True)
            log.error(f"Error en cerrar_mi_ticket: {e}")
    
    @app_commands.command(name="estado_tickets", description="Muestra estadísticas de tickets (Solo staff)")
    async def estado_tickets(self, interaction: nextcord.Interaction):
        """Muestra estadísticas del sistema de tickets"""
        try:
            # Verificar permisos de staff
            if not any(role.id in [OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID] 
                      for role in interaction.user.roles if role.id):
                await interaction.response.send_message(
                    "❌ Solo el staff puede usar este comando",
                    ephemeral=True
                )
                return
            
            data = load_data()
            tickets = data.get("tickets", {})
            
            # Contar tickets por estado
            abiertos = sum(1 for t in tickets.values() if t.get("status") == "abierto")
            cerrados = sum(1 for t in tickets.values() if t.get("status") == "cerrado")
            total = len(tickets)
            
            # Usuarios en cooldown
            cooldown_users = len(self.user_cooldowns)
            
            embed = nextcord.Embed(
                title="📊 Estado del Sistema de Tickets",
                color=0x00E5A8,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="🎫 Tickets Totales", value=str(total), inline=True)
            embed.add_field(name="🟢 Abiertos", value=str(abiertos), inline=True)
            embed.add_field(name="🔴 Cerrados", value=str(cerrados), inline=True)
            embed.add_field(name="⏰ Usuarios en Cooldown", value=str(cooldown_users), inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message("❌ Error obteniendo estadísticas", ephemeral=True)
            log.error(f"Error en estado_tickets: {e}")

class IntegratedTicketView(nextcord.ui.View):
    """Vista integrada para selección de tipos de tickets"""
    
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
            
            # Verificar cooldown y rate limiting
            if self.ticket_commands:
                can_create, seconds_remaining = self.ticket_commands._check_cooldown(user.id)
                if not can_create:
                    minutes = seconds_remaining // 60
                    seconds = seconds_remaining % 60
                    await interaction.followup.send(
                        f"⏰ Debes esperar {minutes}m {seconds}s antes de crear otro ticket",
                        ephemeral=True
                    )
                    return
            
            # Verificar si ya tiene un ticket abierto
            data = load_data()
            user_id = str(user.id)
            has_open_ticket = False
            
            for ticket_id, ticket in data["tickets"].items():
                if (ticket["user_id"] == user_id and 
                    ticket["status"] == "abierto" and 
                    ticket.get("estado_detallado") not in ["cerrado_por_owner", "cerrado"]):
                    has_open_ticket = True
                    break
            
            if has_open_ticket:
                await interaction.followup.send(
                    "❌ Ya tienes un ticket abierto. Por favor, espera a que se resuelva.",
                    ephemeral=True
                )
                return
            
            # Actualizar tracking del usuario
            if self.ticket_commands:
                self.ticket_commands._update_user_ticket_tracking(user.id)
            
            # Crear el ticket usando el sistema integrado
            await self._create_integrated_ticket(guild, user, ticket_type, interaction)
            
        except Exception as e:
            await interaction.followup.send("❌ Error creando ticket", ephemeral=True)
            log.error(f"Error en select_ticket_type: {e}")
    
    async def _create_integrated_ticket(self, guild: nextcord.Guild, user: nextcord.Member, ticket_type: str, interaction: nextcord.Interaction):
        """Crea un ticket usando el sistema integrado"""
        try:
            log.info(f"🚀 Iniciando creación de ticket integrado para {user.display_name} - Tipo: {ticket_type}")
            
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
            
            # Vista de control para el ticket
            control_view = TicketManagementView(ticket_id)
            
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

def setup(bot: commands.Bot):
    """Setup del cog"""
    ticket_cog_instance = IntegratedTicketCommands(bot)
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
