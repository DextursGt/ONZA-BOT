"""
Tickets module for ONZA Bot
Handles ticket creation, management and controls
"""
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
import nextcord
from nextcord.ext import commands

from config import (
    TICKETS_CATEGORY_NAME, TICKETS_LOG_CHANNEL_ID, BRAND_NAME,
    STAFF_ROLE_ID, SUPPORT_ROLE_ID
)
from utils import (
    is_staff, db_execute, db_query_one, log_to_channel, ensure_user_exists,
    generate_ref_code
)
from i18n import t, get_user_lang

class TicketControlsView(nextcord.ui.View):
    """Botones de control para tickets"""
    def __init__(self, ticket_id: int, ticket_user_id: int = None):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.ticket_user_id = ticket_user_id
    
    @nextcord.ui.button(label="Resuelto", style=nextcord.ButtonStyle.success, emoji="✅")
    async def resolved_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede marcar tickets como resueltos.", ephemeral=True)
            return
        
        # Actualizar estado en BD
        await db_execute(
            "UPDATE tickets SET status = 'resolved', last_action_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.ticket_id,)
        )
        
        # Log
        await db_execute(
            "INSERT INTO ticket_logs (ticket_id, action, user_id, data) VALUES (?, ?, ?, ?)",
            (self.ticket_id, "resolved", interaction.user.id, "{}")
        )
        
        # Actualizar permisos del canal
        ticket_data = await db_query_one("SELECT user_id FROM tickets WHERE id = ?", (self.ticket_id,))
        if ticket_data:
            user = interaction.guild.get_member(ticket_data[0])
            if user:
                await interaction.channel.set_permissions(user, send_messages=False)
        
        await interaction.response.send_message("✅ Ticket marcado como resuelto.", ephemeral=True)
        
        # Notificar en log
        lang = await get_user_lang(interaction.user.id)
        await log_to_channel(
            TICKETS_LOG_CHANNEL_ID,
            await t("tickets.resolved", lang, user=interaction.user.mention),
            bot=interaction.client
        )
    
    @nextcord.ui.button(label="Escalar", style=nextcord.ButtonStyle.danger, emoji="⚠️")
    async def escalate_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Solo permitir a usuarios del ticket o staff
        if not is_staff(interaction.user) and interaction.user.id != self.ticket_user_id:
            await interaction.response.send_message("❌ No tienes permiso para escalar este ticket.", ephemeral=True)
            return
        
        # Actualizar estado
        await db_execute(
            "UPDATE tickets SET escalated = 1, last_action_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.ticket_id,)
        )
        
        # Log
        await db_execute(
            "INSERT INTO ticket_logs (ticket_id, action, user_id, data) VALUES (?, ?, ?, ?)",
            (self.ticket_id, "escalated", interaction.user.id, "{}")
        )
        
        # Mencionar staff
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID) if STAFF_ROLE_ID else None
        mention = staff_role.mention if staff_role else "@staff"
        
        await interaction.response.send_message(
            f"⚠️ Ticket escalado. {mention}",
            allowed_mentions=nextcord.AllowedMentions(roles=True)
        )
        
        lang = await get_user_lang(interaction.user.id)
        await log_to_channel(
            TICKETS_LOG_CHANNEL_ID,
            await t("tickets.escalated", lang),
            bot=interaction.client
        )
    
    @nextcord.ui.button(label="Info", style=nextcord.ButtonStyle.primary, emoji="ℹ️")
    async def info_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede ver la información detallada.", ephemeral=True)
            return
        
        # Obtener datos del ticket
        ticket = await db_query_one(
            """SELECT t.*, u.username, o.id as order_id, o.amount_cents, p.name as product_name
               FROM tickets t
               LEFT JOIN users u ON t.user_id = u.discord_id
               LEFT JOIN orders o ON t.order_id = o.id
               LEFT JOIN products p ON o.product_id = p.id
               WHERE t.id = ?""",
            (self.ticket_id,)
        )
        
        if not ticket:
            await interaction.response.send_message("❌ Ticket no encontrado.", ephemeral=True)
            return
        
        # Crear embed con info
        embed = nextcord.Embed(
            title=f"📋 Información del Ticket #{self.ticket_id}",
            color=0x00E5A8
        )
        embed.add_field(name="Usuario", value=f"<@{ticket[1]}> ({ticket[2]})", inline=True)
        embed.add_field(name="Estado", value=ticket[4], inline=True)
        embed.add_field(name="Escalado", value="Sí" if ticket[5] else "No", inline=True)
        
        if ticket[3]:  # order_id
            embed.add_field(name="Orden", value=f"#{ticket[3]}", inline=True)
            embed.add_field(name="Producto", value=ticket[13] or "N/A", inline=True)
            embed.add_field(name="Monto", value=f"${ticket[12]/100:.2f}" if ticket[12] else "N/A", inline=True)
        
        embed.add_field(name="Creado", value=f"<t:{int(datetime.fromisoformat(ticket[7]).timestamp())}:R>", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.ui.button(label="Cerrar", style=nextcord.ButtonStyle.secondary, emoji="🔒")
    async def close_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Verificar permisos: solo staff puede cerrar tickets
        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ Solo el staff puede cerrar tickets. Si necesitas cerrar tu ticket, contacta a un miembro del staff.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("🔒 Cerrando ticket...", ephemeral=True)
        
        # Actualizar BD
        await db_execute(
            "UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.ticket_id,)
        )
        
        # Log
        await db_execute(
            "INSERT INTO ticket_logs (ticket_id, action, user_id, data) VALUES (?, ?, ?, ?)",
            (self.ticket_id, "closed", interaction.user.id, "{}")
        )
        
        # Notificar
        lang = await get_user_lang(interaction.user.id)
        await interaction.channel.send(
            await t("tickets.closed", lang, user=interaction.user.mention)
        )
        
        await log_to_channel(
            TICKETS_LOG_CHANNEL_ID,
            f"🔒 Ticket #{self.ticket_id} cerrado por {interaction.user.mention}",
            bot=interaction.client
        )
        
        # Eliminar canal después de 5 segundos
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user}")
        except:
            pass

class ConfirmView(nextcord.ui.View):
    """Vista de confirmación simple"""
    def __init__(self):
        super().__init__(timeout=30)
        self.value = None
    
    @nextcord.ui.button(label="Confirmar", style=nextcord.ButtonStyle.danger)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        await interaction.response.send_message("Confirmado.", ephemeral=True)
        self.stop()
    
    @nextcord.ui.button(label="Cancelar", style=nextcord.ButtonStyle.secondary)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        await interaction.response.send_message("Cancelado.", ephemeral=True)
        self.stop()

class TicketView(nextcord.ui.View):
    """Panel de creación de tickets"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @nextcord.ui.select(
        placeholder="¿Qué necesitas?",
        min_values=1,
        max_values=1,
        options=[
            nextcord.SelectOption(label="Comprar Producto", value="Comprar", emoji="🛒", description="Hacer un pedido"),
            nextcord.SelectOption(label="Soporte - Problema con mi servicio", value="Soporte-Problema", emoji="⚠️", description="Reportar fallo o problema"),
            nextcord.SelectOption(label="Soporte - Reclamar garantía", value="Soporte-Garantía", emoji="🛡️", description="Activar garantía de producto"),
            nextcord.SelectOption(label="Verificar compra externa", value="Verificación", emoji="✅", description="Verificar pago manual"),
            nextcord.SelectOption(label="Consulta general", value="Consulta", emoji="❓", description="Preguntas o dudas"),
        ]
    )
    async def select_cb(self, select: nextcord.ui.Select, interaction: nextcord.Interaction):
        # Diferir respuesta inmediatamente para evitar timeout
        await interaction.response.defer(ephemeral=True)
        await create_ticket(interaction, select.values[0])

async def get_or_create_category(guild: nextcord.Guild, name: str) -> nextcord.CategoryChannel:
    """Obtener o crear categoría"""
    cat = nextcord.utils.get(guild.categories, name=name)
    if not cat:
        cat = await guild.create_category(name=name, reason=f"{BRAND_NAME} tickets")
    return cat

async def create_ticket(interaction: nextcord.Interaction, servicio: str, order_id: str = None):
    """Crear un nuevo ticket"""
    guild = interaction.guild
    assert guild
    
    # Asegurar que el usuario existe en BD
    await ensure_user_exists(interaction.user.id, str(interaction.user))
    
    # Obtener categoría
    cat = await get_or_create_category(guild, TICKETS_CATEGORY_NAME)
    
    # Permisos del canal
    overwrites = {
        guild.default_role: nextcord.PermissionOverwrite(view_channel=False),
        interaction.user: nextcord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
    }
    
    if STAFF_ROLE_ID:
        role = guild.get_role(STAFF_ROLE_ID)
        if role:
            overwrites[role] = nextcord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )
    
    # Crear canal
    ch = await guild.create_text_channel(
        name=f"ticket-{interaction.user.name[:10]}-{servicio[:10].lower()}",
        category=cat,
        overwrites=overwrites,
        reason=f"Ticket {servicio} abierto por {interaction.user}"
    )
    
    # Registrar en BD
    await db_execute(
        "INSERT INTO tickets (user_id, discord_channel_id) VALUES (?, ?)",
        (interaction.user.id, ch.id)
    )
    
    # Obtener ID del ticket
    ticket_id = (await db_query_one("SELECT id FROM tickets WHERE discord_channel_id = ?", (ch.id,)))[0]
    
    # Mensaje de bienvenida personalizado según tipo
    embed = nextcord.Embed(
        title=f"🎫 Ticket #{ticket_id} - {servicio}",
        description=f"{interaction.user.mention} gracias por abrir un ticket.",
        color=0x00E5A8
    )
    
    # Determinar rol a mencionar según tipo de ticket
    mention_role = None
    
    # Tickets de compra
    if servicio == "Comprar":
        embed.description += f"\n\n🛒 **Quiero hacer un pedido**"
        embed.add_field(
            name="📦 Productos disponibles",
            value="Consulta con nuestro staff los productos y precios actuales.",
            inline=False
        )
        
        embed.add_field(
            name="📝 Proceso de compra",
            value="1️⃣ Dinos qué producto necesitas\n2️⃣ Te enviaremos el link de pago\n3️⃣ Recibirás el producto al instante",
            inline=False
        )
        
        # Mencionar a Operaciones para compras
        if STAFF_ROLE_ID:
            mention_role = interaction.guild.get_role(STAFF_ROLE_ID)
            
    # Tickets de soporte
    elif servicio.startswith("Soporte-"):
        tipo_soporte = servicio.replace("Soporte-", "")
        embed.description += f"\n\n⚠️ **Tipo de soporte:** {tipo_soporte}"
        
        if tipo_soporte == "Problema":
            embed.add_field(
                name="🔧 Información necesaria",
                value="Por favor describe:\n• ¿Qué servicio tienes problema?\n• ¿Cuándo empezó el problema?\n• ¿Qué error ves exactamente?",
                inline=False
            )
        elif tipo_soporte == "Garantía":
            embed.add_field(
                name="🛡️ Reclamo de Garantía",
                value="Por favor proporciona:\n• ID de tu orden\n• Descripción del problema\n• Capturas de pantalla si es posible",
                inline=False
            )
            
        # Mencionar a Soporte
        if SUPPORT_ROLE_ID:
            mention_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
            
    # Verificación
    elif servicio == "Verificación":
        embed.description += "\n\n✅ **Verificación de compra externa**"
        embed.add_field(
            name="📋 Información requerida",
            value="Por favor envía:\n• Captura del pago (oculta datos sensibles)\n• Método de pago usado\n• Fecha y hora del pago\n• Monto pagado",
            inline=False
        )
        
    # Consulta general
    elif servicio == "Consulta":
        embed.description += "\n\n❓ **Consulta general**"
        embed.add_field(
            name="💬 ¿En qué podemos ayudarte?",
            value="Por favor describe tu consulta de forma detallada.\n\nSi es sobre un producto específico, indícanos cuál.",
            inline=False
        )
    
    # Agregar campo de tiempo estimado
    embed.add_field(
        name="⏱️ Tiempo de respuesta",
        value="**Máximo 50 minutos**\n🟢 Lun-Vie: 9:00 - 23:00\n🟡 Sáb-Dom: 10:00 - 22:00",
        inline=True
    )
    
    embed.set_footer(text=f"{BRAND_NAME} • Usa los botones para acciones rápidas")
    
    # Enviar mensaje con controles (pasando el ID del usuario dueño del ticket)
    controls = TicketControlsView(ticket_id, interaction.user.id)
    await ch.send(embed=embed, view=controls)
    
    # Responder a la interacción
    # Si ya se difirió la respuesta, usar followup
    if interaction.response.is_done():
        await interaction.followup.send(
            f"✅ **Ticket creado exitosamente!**\n\n🎫 **Canal:** {ch.mention}\n📋 **Servicio:** {servicio}\n👤 **Usuario:** {interaction.user.mention}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"✅ **Ticket creado exitosamente!**\n\n🎫 **Canal:** {ch.mention}\n📋 **Servicio:** {servicio}\n👤 **Usuario:** {interaction.user.mention}",
            ephemeral=True
        )
    
    # Log en canal de logs si está configurado
    try:
        from utils import log_accion
        await log_accion("Ticket Creado", interaction.user.display_name, f"Canal: {ch.name}, Servicio: {servicio}")
    except Exception as e:
        print(f"Error logging ticket creation: {e}")
