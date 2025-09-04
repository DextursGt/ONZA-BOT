

"""
ONZA Bot - Bot de Discord Optimizado
Versión: 3.0
Autor: ONZA Team
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

import nextcord
from nextcord.ext import commands, tasks
from nextcord import ui

# Importar módulos optimizados
from config import *
from utils import log, ensure_db, is_staff, db_execute, db_query_one, db_query_all
from i18n import t, get_user_lang
from tickets import (
    TicketView, create_ticket, TicketControlsView, ConfirmView,
    get_or_create_category
)

# Importar webserver para keep-alive
import webserver

# Store database imports
from db import (
    ensure_store_db, sync_legacy_products_into_store,
    upsert_product, soft_delete_product, get_product, list_products,
    add_option, delete_option, list_options, cheapest_options_by_sku
)

# Sistema de publicación simplificado

# IA opcional (para futuras funcionalidades)
try:
    from openai import AsyncOpenAI
    oaiclient = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except ImportError:
    oaiclient = None

# Bot setup
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== EVENTOS DEL BOT ==========

async def actualizar_mensajes_interactivos(guild):
    """Actualizar automáticamente todos los mensajes interactivos del servidor"""
    try:
        log.info("Iniciando actualización de mensajes interactivos...")
        
        # Buscar y actualizar el panel de tickets en el canal de tickets
        canal_tickets = guild.get_channel(CANALES_BOT.get('tickets'))
        log.info(f"Canal de tickets encontrado: {canal_tickets}")
        
        if canal_tickets:
            await actualizar_panel_tickets(canal_tickets)
        else:
            log.warning("No se encontró el canal de tickets")
        
        # Aquí puedes agregar más mensajes interactivos que necesiten actualización
        # Por ejemplo: paneles de bienvenida, reglas, etc.
        
        log.info("Mensajes interactivos actualizados correctamente")
        
    except Exception as e:
        log.error(f"Error actualizando mensajes interactivos: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")

async def actualizar_panel_tickets(canal):
    """Actualizar el panel de tickets en el canal especificado"""
    try:
        # Limpiar mensajes antiguos del panel
        async for message in canal.history(limit=50):
            # Buscar mensajes que contengan el panel de tickets
            if (message.author == bot.user and 
                message.embeds and 
                any("🎫 Soporte" in embed.title for embed in message.embeds)):
                await message.delete()
                break
        
        # Crear y publicar el nuevo panel
        view = TicketView()
        embed = nextcord.Embed(
            title=f"🎫 Soporte {BRAND_NAME}",
            description="Elige un servicio para abrir tu ticket privado.\n\n**Horario de atención:** 24/7\n**Tiempo de respuesta:** < 50 minutos",
            color=0x00E5A8
        )
        embed.add_field(
            name="📋 Servicios disponibles",
            value="• **Compras:** Haz tu pedido\n• **Verificación:** Confirmar tu compra\n• **Garantía:** Reclamar garantía de producto\n• **Otro:** Consultas generales",
            inline=False
        )
        embed.set_footer(text="Selecciona una opción del menú desplegable")
        
        await canal.send(embed=embed, view=view)
        log.info(f"Panel de tickets actualizado en {canal.name}")
        
    except Exception as e:
        log.error(f"Error actualizando panel de tickets: {e}")



@bot.event
async def on_ready():
    """Evento cuando el bot está listo"""
    log.info(f"Bot conectado como {bot.user}")
    
    try:
        # Inicializar base de datos del bot
        log.info("🔧 Inicializando base de datos del bot...")
        from init_db import init_bot_database
        db_result = await init_bot_database()
        if db_result:
            log.info("✅ Base de datos del bot inicializada correctamente")
        else:
            log.error("❌ Error inicializando base de datos del bot")
            # Intentar inicializar nuevamente
            log.info("🔄 Reintentando inicialización de base de datos...")
            db_result = await init_bot_database()
            if db_result:
                log.info("✅ Base de datos del bot inicializada en segundo intento")
            else:
                log.error("❌ Error persistente en inicialización de base de datos")
        
        # Inicializar base de datos de la tienda
        log.info("🔧 Inicializando base de datos de la tienda...")
        await ensure_store_db()
        log.info("✅ Bases de datos inicializadas")
        
        # Sincronizar comandos slash primero
        if GUILD_ID:
            try:
                await bot.sync_all_application_commands()
                log.info(f"Comandos sincronizados en guild {GUILD_ID}")
            except Exception as e:
                log.error(f"Error sincronizando comandos: {e}")
        
        # Inicializar canales automáticamente (después de comandos)
        if bot.guilds:
            await actualizar_canales_bot(bot.guilds[0])
            log.info("Canales del bot inicializados automáticamente")
            
            # Actualizar mensajes interactivos automáticamente
            await actualizar_mensajes_interactivos(bot.guilds[0])
            log.info("Mensajes interactivos actualizados automáticamente")
        
        # Iniciar tareas de fondo solo si no están corriendo
        if not maintenance_loop.is_running():
            maintenance_loop.start()
        
        log.info("Bot completamente inicializado")
        
    except Exception as e:
        log.error(f"Error en evento on_ready: {e}")
        # Continuar con la sincronización de comandos incluso si hay errores
        try:
            if GUILD_ID:
                await bot.sync_all_application_commands()
                log.info(f"Comandos sincronizados en guild {GUILD_ID}")
        except Exception as sync_error:
            log.error(f"Error crítico sincronizando comandos: {sync_error}")

@bot.event
async def on_guild_join(guild):
    """Evento cuando el bot se une a un servidor"""
    log.info(f"Bot unido a servidor: {guild.name} (ID: {guild.id})")

@bot.event
async def on_member_join(member):
    """Evento cuando un usuario se une al servidor"""
    try:
        log.info(f"Usuario unido: {member.display_name} ({member.id})")
        
        # Asignar rol de cliente automáticamente
        client_role = member.guild.get_role(CLIENT_ROLE_ID)
        if client_role:
            try:
                await member.add_roles(client_role, reason="Auto-asignación de rol de cliente")
                log.info(f"Rol de cliente asignado a {member.display_name}")
            except Exception as e:
                log.error(f"Error asignando rol de cliente a {member.display_name}: {e}")
        
        # Enviar mensaje de bienvenida
        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            # Crear embed de bienvenida bonito
            embed = nextcord.Embed(
                title="🎉 ¡Bienvenido a ONZA! 🎉",
                description=f"¡Hola {member.mention}! Te damos la bienvenida a nuestro servidor.",
                color=0x00E5A8,  # Color verde ONZA
                timestamp=nextcord.utils.utcnow()
            )
            
            # Agregar información útil
            embed.add_field(
                name="🛒 ¿Cómo comprar?",
                value=f"Para realizar compras, visita el canal {member.guild.get_channel(HOW_TO_BUY_CHANNEL_ID).mention if member.guild.get_channel(HOW_TO_BUY_CHANNEL_ID) else '#como-comprar'}",
                inline=False
            )
            
            embed.add_field(
                name="🎫 Soporte",
                value="Si necesitas ayuda, abre un ticket en el canal correspondiente",
                inline=False
            )
            
            embed.add_field(
                name="📋 Reglas",
                value="Por favor, lee las reglas del servidor para una mejor experiencia",
                inline=False
            )
            
            # Agregar imagen del servidor si está disponible
            if member.guild.icon:
                embed.set_thumbnail(url=member.guild.icon.url)
            
            # Agregar footer
            embed.set_footer(
                text=f"Miembro #{member.guild.member_count}",
                icon_url=member.display_avatar.url
            )
            
            try:
                await welcome_channel.send(content=member.mention, embed=embed)
                log.info(f"Mensaje de bienvenida enviado para {member.display_name}")
            except Exception as e:
                log.error(f"Error enviando mensaje de bienvenida: {e}")
        else:
            log.warning(f"Canal de bienvenida no encontrado (ID: {WELCOME_CHANNEL_ID})")
            
    except Exception as e:
        log.error(f"Error en evento on_member_join: {e}")

# ========== COMANDOS PRINCIPALES ==========





@bot.slash_command(name="panel", description="Publica el panel de tickets (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def panel(interaction: nextcord.Interaction):
    if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
        lang = await get_user_lang(interaction.user.id)
        await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
        return
    
    view = TicketView()
    embed = nextcord.Embed(
        title=f"🎫 Soporte {BRAND_NAME}",
        description="Elige un servicio para abrir tu ticket privado.\n\n**Horario de atención:** 24/7\n**Tiempo de respuesta:** < 50 minutos",
        color=0x00E5A8
    )
    embed.add_field(
        name="📋 Servicios disponibles",
        value="• **Compras:** Haz tu pedido\n• **Verificación:** Confirmar tu compra\n• **Garantía:** Reclamar garantía de producto\n• **Otro:** Consultas generales",
        inline=False
    )
    embed.set_footer(text="Selecciona una opción del menú desplegable")
    
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("Panel publicado.", ephemeral=True)

    # Log de la acción
    await log_accion("Panel de Tickets Publicado", interaction.user.display_name)

# Comando de idioma eliminado - No necesario para el bot simplificado



@bot.slash_command(name="reseña", description="Dejar una reseña", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def resena(interaction: nextcord.Interaction,
                rating: int = nextcord.SlashOption(description="Calificación (1-5)", min_value=1, max_value=5),
                comentario: str = nextcord.SlashOption(description="Tu comentario"),
                order_id: Optional[str] = nextcord.SlashOption(description="ID de orden (opcional)", required=False)):
    lang = await get_user_lang(interaction.user.id)
    from utils import ensure_user_exists
    await ensure_user_exists(interaction.user.id, str(interaction.user))
    
    # Verificar si tiene órdenes
    if order_id:
        order = await db_query_one(
            "SELECT * FROM orders WHERE id = ? AND user_id = ? AND status = 'delivered'",
            (order_id, interaction.user.id)
        )
        if not order:
            await interaction.response.send_message("❌ Orden no encontrada o no entregada.", ephemeral=True)
            return
    else:
        # Usar la orden más reciente entregada
        order = await db_query_one(
            "SELECT * FROM orders WHERE user_id = ? AND status = 'delivered' ORDER BY delivered_at DESC LIMIT 1",
            (interaction.user.id,)
        )
        if not order:
            await interaction.response.send_message("❌ No tienes órdenes entregadas para reseñar.", ephemeral=True)
            return
        order_id = order[0]
    
    # Verificar si ya existe reseña
    existing = await db_query_one(
        "SELECT id FROM reviews WHERE user_id = ? AND order_id = ?",
        (interaction.user.id, order_id)
    )
    
    if existing:
        await interaction.response.send_message(await t("review.already", lang), ephemeral=True)
        return
    
    # Crear reseña
    await db_execute(
        "INSERT INTO reviews (user_id, order_id, rating, comment) VALUES (?, ?, ?, ?)",
        (interaction.user.id, order_id, rating, comentario[:500])
    )
    
    await interaction.response.send_message(await t("review.thanks", lang), ephemeral=True)
    
    # Notificar a staff
    if REVIEWS_CHANNEL_ID:
        embed = nextcord.Embed(
            title="⭐ Nueva Reseña Pendiente",
            description=f"**Usuario:** {interaction.user.mention}\n**Rating:** {'⭐' * rating}\n**Comentario:** {comentario[:200]}",
            color=0xffff00,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Usa /reseña_aprobar para aprobar")
        # Enviar log al canal de reseñas si está configurado
        if REVIEWS_CHANNEL_ID:
            try:
                channel = bot.get_channel(REVIEWS_CHANNEL_ID)
                if channel:
                    await channel.send(embed=embed)
            except Exception as e:
                log.error(f"Error enviando log de reseña: {e}")

@bot.slash_command(name="reseña_aprobar", description="Aprobar reseña (staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def resena_aprobar(interaction: nextcord.Interaction,
                        review_id: Optional[int] = nextcord.SlashOption(description="ID de reseña", required=False),
                        usuario: Optional[nextcord.Member] = nextcord.SlashOption(description="O usuario", required=False)):
    if not is_staff(interaction.user):
        lang = await get_user_lang(interaction.user.id)
        await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
        return
    
    # Buscar reseña
    if review_id:
        review = await db_query_one("SELECT * FROM reviews WHERE id = ?", (review_id,))
    elif usuario:
        review = await db_query_one(
            "SELECT * FROM reviews WHERE user_id = ? AND approved = 0 ORDER BY created_at DESC LIMIT 1",
            (usuario.id,)
        )
    else:
        # Mostrar pendientes
        reviews = await db_query_all(
            "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.discord_id WHERE r.approved = 0 LIMIT 10"
        )
        
        if not reviews:
            await interaction.response.send_message("No hay reseñas pendientes.", ephemeral=True)
            return
        
        embed = nextcord.Embed(title="📋 Reseñas Pendientes", color=0x00E5A8)
        for r in reviews:
            embed.add_field(
                name=f"ID: {r[0]} - {r[10]} - {'⭐' * r[3]}",
                value=f"{r[4][:100]}...",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not review:
        await interaction.response.send_message("❌ Reseña no encontrada.", ephemeral=True)
        return
    
    # Aprobar
    await db_execute("UPDATE reviews SET approved = 1 WHERE id = ?", (review[0],))
    
    # Publicar en canal
    if REVIEWS_CHANNEL_ID:
        user = bot.get_user(review[1])
        product = await db_query_one(
            "SELECT p.name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?",
            (review[2],)
        )
        
        embed = nextcord.Embed(
            title=f"{'⭐' * review[3]} {product[0] if product else 'Producto'}",
            description=f'"{review[4]}"',
            color=0x00E5A8,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_author(
            name=user.display_name if user else "Cliente",
            icon_url=user.avatar.url if user and user.avatar else None
        )
        embed.set_footer(text=f"{BRAND_NAME} • Reseña verificada")
        
        channel = bot.get_channel(REVIEWS_CHANNEL_ID)
        if channel:
            msg = await channel.send(embed=embed)
            await db_execute(
                "UPDATE reviews SET posted_message_id = ?, channel_id = ? WHERE id = ?",
                (msg.id, REVIEWS_CHANNEL_ID, review[0])
            )
    
    await interaction.response.send_message("✅ Reseña aprobada y publicada.", ephemeral=True)

# ========== COMANDOS DE AYUDA ==========

@bot.slash_command(name="help", description="Ver comandos disponibles", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def help_command(interaction: nextcord.Interaction):
    """Comando de ayuda para usuarios"""
    lang = await get_user_lang(interaction.user.id)
    
    if is_staff(interaction.user):
        # Ayuda para staff
        embed = nextcord.Embed(
            title="🛠️ **Comandos de Staff**",
            description="Comandos administrativos disponibles:",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="🎫 **Tickets**",
            value="`/panel` - Publicar panel de tickets\n`/limpiar_tickets` - Limpiar tickets cerrados",
            inline=False
        )
        
        embed.add_field(
            name="📢 **Publicación**",
            value="`/publicar_bot` - Publicar mensaje personalizado\n`/servicios` - Publicar mensaje de servicios\n`/publicar_metodos_pago` - Publicar métodos de pago visible para todos\n`/actualizar_canales` - Actualizar canales automáticamente",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ **Administración**",
            value="`/actualizar_canales` - Actualizar canales automáticamente\n`/canal_id` - Obtener ID de un canal\n`/limpiar` - Limpiar mensajes del canal\n`/sync_commands` - Sincronizar comandos slash\n`/reiniciar_render` - Información para reiniciar Render",
            inline=False
        )
        
        embed.add_field(
            name="🔨 **Moderación**",
            value="`/banear` - Banear un usuario del servidor",
            inline=False
        )
        
        embed.add_field(
            name="📊 **Reseñas**",
            value="`/reseña_aprobar` - Aprobar reseñas de usuarios",
            inline=False
        )
        
        embed.set_footer(text="ONZA Bot • Comandos de Staff")
        
    else:
        # Ayuda para usuarios normales
        embed = nextcord.Embed(
            title="🤖 **Comandos de Usuario**",
            description="Comandos disponibles para todos:",
            color=0x5865F2,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="🎫 **Tickets**",
            value="Ve al canal #abrir-ticket y usa el panel de tickets publicado",
            inline=False
        )
        
        embed.add_field(
            name="❓ **Información**",
            value="`/metodos_pago` - Ver métodos de pago disponibles",
            inline=False
        )
        
        embed.add_field(
            name="⭐ **Reseñas**",
            value="`/reseña [rating] [comentario]` - Dejar reseña",
            inline=False
        )
        
        embed.set_footer(text="ONZA Bot • Comandos de Usuario")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== COMANDOS RECREATIVOS ==========

@bot.slash_command(name="metodos_pago", description="Ver métodos de pago disponibles", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def metodos_pago(interaction: nextcord.Interaction):
    """Mostrar métodos de pago disponibles"""
    embed = nextcord.Embed(
        title="💳 **Métodos de Pago Disponibles**",
        description="Aquí tienes todas las opciones para realizar tu pago:",
        color=0x00FF00,
        timestamp=nextcord.utils.utcnow()
    )
    
    for metodo in METODOS_PAGO:
        embed.add_field(
            name=metodo,
            value="Disponible para pagos",
            inline=False
        )
    
    embed.set_footer(text="ONZA Bot • Métodos de Pago")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log de la acción
    await log_accion("Métodos de Pago Consultados", interaction.user.display_name)

@bot.slash_command(name="publicar_metodos_pago", description="Publicar métodos de pago visible para todos (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def publicar_metodos_pago(interaction: nextcord.Interaction):
    """Publicar métodos de pago como mensaje visible para todos los usuarios"""
    # Verificar que sea staff
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    # Crear embed con métodos de pago
    embed = nextcord.Embed(
        title="💳 **Métodos de Pago Disponibles**",
        description="Aquí tienes todas las opciones para realizar tu pago:",
        color=0x00E5A8,  # Color verde ONZA
        timestamp=nextcord.utils.utcnow()
    )
    
    for metodo in METODOS_PAGO:
        embed.add_field(
            name=metodo,
            value="✅ Disponible para pagos",
            inline=False
        )
    
    embed.add_field(
        name="📝 **Información Importante**",
        value="• Todos los pagos son seguros y verificados\n• Para realizar una compra, abre un ticket\n• El staff te ayudará con el proceso de pago",
        inline=False
    )
    
    embed.set_footer(text="ONZA Bot • Métodos de Pago Oficiales", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    # Enviar mensaje visible para todos
    await interaction.response.send_message(embed=embed)
    
    # Log de la acción
    await log_accion("Métodos de Pago Publicados", interaction.user.display_name, "Mensaje visible para todos los usuarios")







@bot.slash_command(name="servicios", description="Publicar mensaje de servicios (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def servicios(interaction: nextcord.Interaction):
    """Publicar mensaje de servicios como mensaje fijado"""
    if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
        
    # Abrir modal para configurar el mensaje de servicios
    modal = ServiciosModal()
    await interaction.response.send_modal(modal)

class ServiciosModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Configurar Mensaje de Servicios")
        
        self.titulo = ui.TextInput(
            label="Título del mensaje",
            placeholder="🛠️ Servicios Disponibles",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.descripcion = ui.TextInput(
            label="Descripción principal",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Nuestros servicios principales están disponibles en el catálogo...",
            required=True,
            max_length=1024
        )
        self.add_item(self.descripcion)
        
        self.servicios_texto = ui.TextInput(
            label="Lista de servicios",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="• Desarrollo web\n• Aplicaciones móviles\n• Bots de Discord\n• Logos y branding",
            required=True,
            max_length=1024
        )
        self.add_item(self.servicios_texto)
        
        self.instrucciones = ui.TextInput(
            label="Instrucciones para cotizar",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Para cotizar, ve al canal #abrir-ticket y usa el panel de tickets...",
            required=True,
            max_length=1024
        )
        self.add_item(self.instrucciones)
        
        self.color_hex = ui.TextInput(
            label="Color del embed en hex (opcional)",
            placeholder="00E5A8 (sin #)",
            required=False,
            max_length=6
        )
        self.add_item(self.color_hex)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Crear vista para selección de canal
            view = VistaSeleccionCanalServicios(self)
            
            # Previsualización del mensaje
            try:
                color_value = self.color_hex.value if self.color_hex.value else "00E5A8"
                color = int(color_value.replace("#", ""), 16)
            except:
                color = 0x00E5A8
            
            embed_preview = nextcord.Embed(
                title=self.titulo.value,
                description=self.descripcion.value,
                color=color,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed_preview.add_field(
                name="📋 **Servicios Disponibles**",
                value=self.servicios_texto.value,
                inline=False
            )
            
            embed_preview.add_field(
                name="🎫 **Para Cotizar**",
                value=self.instrucciones.value,
                inline=False
            )
            
            embed_preview.set_footer(text=f"{BRAND_NAME} • Servicios")
            
            # Mostrar previsualización
            await interaction.response.send_message(
                content="**📝 Previsualización del mensaje de servicios:**",
                embed=embed_preview,
                view=view,
                ephemeral=True
            )

        except Exception as e:
            log.error(f"Error en modal de servicios: {e}")
            await interaction.response.send_message(
                "❌ **Error al crear el mensaje**",
                ephemeral=True
            )

class VistaSeleccionCanalServicios(ui.View):
    def __init__(self, modal: ServiciosModal):
        super().__init__(timeout=180)
        self.modal = modal
        self.selected_channel = None
    
    @ui.channel_select(
        placeholder="Selecciona el canal donde publicar",
        min_values=1,
        max_values=1,
        channel_types=[nextcord.ChannelType.text, nextcord.ChannelType.news]
    )
    async def channel_select(self, select: ui.ChannelSelect, interaction: nextcord.Interaction):
        self.selected_channel = select.values[0]
        
        # Confirmar publicación
        confirm_view = VistaConfirmarPublicacionServicios(self.modal, self.selected_channel)
        await interaction.response.edit_message(
            content=f"**¿Publicar este mensaje de servicios en {self.selected_channel.mention}?**\n\n_El mensaje será publicado como {interaction.client.user.mention} y se fijará automáticamente_",
            view=confirm_view
        )

class VistaConfirmarPublicacionServicios(ui.View):
    def __init__(self, modal: ServiciosModal, channel: nextcord.TextChannel):
        super().__init__(timeout=60)
        self.modal = modal
        self.channel = channel
    
    @ui.button(label="Publicar y Fijar", style=nextcord.ButtonStyle.success)
    async def confirm_button(self, button: ui.Button, interaction: nextcord.Interaction):
        try:
            # Preparar embed
            try:
                color_value = self.modal.color_hex.value if self.modal.color_hex.value else "00E5A8"
                color = int(color_value.replace("#", ""), 16)
            except:
                color = 0x00E5A8
            
            embed = nextcord.Embed(
                title=self.modal.titulo.value,
                description=self.modal.descripcion.value,
                color=color,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📋 **Servicios Disponibles**",
                value=self.modal.servicios_texto.value,
                inline=False
            )
            
            embed.add_field(
                name="🎫 **Para Cotizar**",
                value=self.modal.instrucciones.value,
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Servicios")
            
            # Publicar mensaje
            msg = await self.channel.send(embed=embed)
            
            # Fijar el mensaje
            try:
                await msg.pin()
            except Exception as e:
                log.warning(f"No se pudo fijar el mensaje: {e}")
            
            # Confirmar al usuario
            await interaction.response.edit_message(
                content=f"✅ Mensaje de servicios publicado y fijado en {self.channel.mention}\n\n[Ver mensaje]({msg.jump_url})",
                embed=None,
                view=None
            )
            
            # Log detallado
            try:
                log_embed = nextcord.Embed(
                    title="📢 Mensaje de Servicios Publicado",
                    description=f"**Staff:** {interaction.user.mention}\n**Canal:** {self.channel.mention}\n**Hora:** <t:{int(datetime.now().timestamp())}:F>",
                    color=0x00E5A8
                )
                
                log_embed.add_field(
                    name="Título",
                    value=self.modal.titulo.value,
                    inline=False
                )
                
                # Usar el sistema de logs detallado
                if 'logs' in CANALES_BOT and GUILD_ID:
                    guild = interaction.client.get_guild(GUILD_ID)
                    if guild:
                        canal_logs = guild.get_channel(CANALES_BOT['logs'])
                        if canal_logs:
                            await canal_logs.send(embed=log_embed)
            except Exception as e:
                log.error(f"Error enviando log detallado: {e}")
                # Fallback al sistema simple
                try:
                    await log_accion("Mensaje de Servicios Publicado", interaction.user.display_name, f"Canal: {self.channel.name}")
                except:
                    pass
            
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error al publicar mensaje: {str(e)}",
                embed=None,
                view=None
            )
    
    @ui.button(label="Cancelar", style=nextcord.ButtonStyle.danger)
    async def cancel_button(self, button: ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(
            content="❌ Publicación cancelada.",
            embed=None,
            view=None
        )

# ========== COMANDOS DE ADMINISTRACIÓN ==========

@bot.slash_command(name="configurar_canal", description="Configurar canales del bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def configurar_canal(interaction: nextcord.Interaction,
                          tipo: str = nextcord.SlashOption(description="Tipo de canal", choices=["tickets", "logs", "reseñas", "anuncios"]),
                          canal: nextcord.TextChannel = nextcord.SlashOption(description="Canal a configurar")):
    """Configurar canales del bot"""
    if not isinstance(interaction.user, nextcord.Member) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo los administradores pueden usar este comando.", ephemeral=True)
        return
    
    # Aquí podrías guardar la configuración en base de datos
    await interaction.response.send_message(
        f"✅ Canal {canal.mention} configurado como canal de **{tipo}**",
        ephemeral=True
    )



@bot.slash_command(name="limpiar", description="Limpiar mensajes del canal (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def limpiar(interaction: nextcord.Interaction,
                  cantidad: int = nextcord.SlashOption(description="Cantidad de mensajes a eliminar", min_value=1, max_value=100)):
    """Limpiar mensajes del canal"""
    if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    if not interaction.channel.permissions_for(interaction.user).manage_messages:
        await interaction.response.send_message("❌ No tienes permisos para eliminar mensajes.", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    
    try:
        deleted = await interaction.channel.purge(limit=cantidad + 1)  # +1 para incluir el comando
        await interaction.followup.send(f"✅ **{len(deleted)-1} mensajes eliminados** del canal.", ephemeral=True)
        
        # Log de la acción
        await log_accion("Canal Limpiado", interaction.user.display_name, f"Canal: {interaction.channel.name}, Mensajes: {len(deleted)-1}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error al eliminar mensajes: {str(e)}", ephemeral=True)

@bot.slash_command(name="limpiar_tickets", description="Limpiar tickets cerrados (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def limpiar_tickets(interaction: nextcord.Interaction):
    """Limpiar tickets cerrados del servidor"""
    if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Buscar canales de tickets cerrados
        tickets_eliminados = 0
        canales_eliminados = 0
        
        # Obtener la categoría de tickets
        categoria = get_or_create_category(interaction.guild, TICKETS_CATEGORY_NAME)
        
        if categoria:
            # Buscar canales de tickets cerrados
            for canal in categoria.channels:
                if isinstance(canal, nextcord.TextChannel) and canal.name.startswith('ticket-'):
                    try:
                        # Verificar si el ticket está cerrado (sin permisos de usuarios)
                        overwrites = canal.overwrites
                        usuario_ticket = None
                        
                        # Buscar el usuario del ticket
                        for target, overwrite in overwrites.items():
                            if isinstance(target, nextcord.Member) and overwrite.send_messages is False:
                                usuario_ticket = target
                            break
            
                        # Si el usuario no puede escribir, el ticket está cerrado
                        if usuario_ticket and overwrites.get(usuario_ticket, {}).send_messages is False:
                            await canal.delete(reason="Ticket cerrado - Limpieza automática")
                            tickets_eliminados += 1
                            canales_eliminados += 1
                            
                    except Exception as e:
                        log.error(f"Error eliminando canal {canal.name}: {e}")
                        continue
        
        if tickets_eliminados > 0:
            await interaction.followup.send(
                f"✅ **Limpieza completada:**\n"
                f"• **Tickets eliminados:** {tickets_eliminados}\n"
                f"• **Canales eliminados:** {canales_eliminados}",
                    ephemeral=True
                )
            
            # Log de la acción
            await log_accion("Tickets Limpiados", interaction.user.display_name, f"Tickets: {tickets_eliminados}, Canales: {canales_eliminados}")
        else:
            await interaction.followup.send("ℹ️ **No hay tickets cerrados para limpiar.**", ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ **Error al limpiar tickets:** {str(e)}", ephemeral=True)
        log.error(f"Error en limpiar_tickets: {e}")

# ========== COMANDO EMBED ==========

@bot.slash_command(name="publicar_bot", description="Publicar un mensaje personalizado como el bot (staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def publicar_bot(interaction: nextcord.Interaction):
    if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    # Abrir modal para escribir el mensaje
    modal = PublicarMensajeModal()
    await interaction.response.send_modal(modal)

class PublicarMensajeModal(ui.Modal):
    def __init__(self):
        super().__init__(title="Publicar Mensaje Personalizado")
        
        self.contenido = ui.TextInput(
            label="Contenido del mensaje",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Escribe el mensaje aquí. Puedes usar emojis 🎉, **negrita**, *cursiva*, etc.",
            required=True,
            max_length=2000
        )
        self.add_item(self.contenido)
        
        self.titulo_embed = ui.TextInput(
            label="Título del embed (opcional)",
            placeholder="Título del mensaje embebido",
            required=False,
            max_length=256
        )
        self.add_item(self.titulo_embed)
        
        self.descripcion_embed = ui.TextInput(
            label="Descripción del embed (opcional)",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Si quieres usar embed, escribe la descripción aquí",
            required=False,
            max_length=1024
        )
        self.add_item(self.descripcion_embed)
        
        self.imagen_url = ui.TextInput(
            label="URL de imagen (opcional)",
            placeholder="https://ejemplo.com/imagen.png",
            required=False,
            max_length=500
        )
        self.add_item(self.imagen_url)
        
        self.color_hex = ui.TextInput(
            label="Color del embed en hex (opcional)",
            placeholder="00E5A8 (sin #)",
            required=False,
            max_length=6
        )
        self.add_item(self.color_hex)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Crear vista para selección de canal
            view = VistaSeleccionCanal(self)
            
            # Previsualización del mensaje
            embed_preview = None
            if self.titulo_embed.value or self.descripcion_embed.value:
                try:
                    # Si no hay valor, usar el predeterminado
                    color_value = self.color_hex.value if self.color_hex.value else "00E5A8"
                    color = int(color_value.replace("#", ""), 16)
                except:
                    color = 0x00E5A8
                
                embed_preview = nextcord.Embed(
                    title=self.titulo_embed.value or None,
                    description=self.descripcion_embed.value or None,
                    color=color
                )
                
                if self.imagen_url.value:
                    embed_preview.set_image(url=self.imagen_url.value)
                
                embed_preview.set_footer(text=f"{BRAND_NAME} • Mensaje del staff")
            
            # Mostrar previsualización
            preview_text = "**📝 Previsualización del mensaje:**\n\n"
            if not embed_preview:
                preview_text += self.contenido.value[:500]
                if len(self.contenido.value) > 500:
                    preview_text += "..."
            
            await interaction.response.send_message(
                content=preview_text,
                embed=embed_preview,
                view=view,
                ephemeral=True
            )

        except Exception as e:
            log.error(f"Error en modal: {e}")
            await interaction.response.send_message(
                "❌ **Error al crear el mensaje**",
                ephemeral=True
            )

class VistaSeleccionCanal(ui.View):
    def __init__(self, modal: PublicarMensajeModal):
        super().__init__(timeout=180)
        self.modal = modal
        self.selected_channel = None
    
    @ui.channel_select(
        placeholder="Selecciona el canal donde publicar",
        min_values=1,
        max_values=1,
        channel_types=[nextcord.ChannelType.text, nextcord.ChannelType.news]
    )
    async def channel_select(self, select: ui.ChannelSelect, interaction: nextcord.Interaction):
        self.selected_channel = select.values[0]
        
        # Confirmar publicación
        confirm_view = VistaConfirmarPublicacion(self.modal, self.selected_channel)
        await interaction.response.edit_message(
            content=f"**¿Publicar este mensaje en {self.selected_channel.mention}?**\n\n_El mensaje será publicado como {interaction.client.user.mention}_",
            view=confirm_view
        )

class VistaConfirmarPublicacion(ui.View):
    def __init__(self, modal: PublicarMensajeModal, channel: nextcord.TextChannel):
        super().__init__(timeout=60)
        self.modal = modal
        self.channel = channel
    
    @ui.button(label="Publicar", style=nextcord.ButtonStyle.success)
    async def confirm_button(self, button: ui.Button, interaction: nextcord.Interaction):
        try:
            # Preparar embed si es necesario
            embed = None
            if self.modal.titulo_embed.value or self.modal.descripcion_embed.value:
                try:
                    # Si no hay valor, usar el predeterminado
                    color_value = self.modal.color_hex.value if self.modal.color_hex.value else "00E5A8"
                    color = int(color_value.replace("#", ""), 16)
                except:
                    color = 0x00E5A8
                
                embed = nextcord.Embed(
                    title=self.modal.titulo_embed.value or None,
                    description=self.modal.descripcion_embed.value or None,
                    color=color
                )
                
                if self.modal.imagen_url.value:
                    embed.set_image(url=self.modal.imagen_url.value)
                
                embed.set_footer(text=f"ONZA Bot • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Publicar mensaje
            msg = await self.channel.send(
                content=self.modal.contenido.value if not embed else None,
                embed=embed
            )
            
            # Confirmar al usuario
            await interaction.response.edit_message(
                content=f"✅ Mensaje publicado exitosamente en {self.channel.mention}\n\n[Ver mensaje]({msg.jump_url})",
                embed=None,
                view=None
            )
            
            # Log detallado como en el bot antiguo
            try:
                log_embed = nextcord.Embed(
                    title="📢 Mensaje Publicado por Staff",
                    description=f"**Staff:** {interaction.user.mention}\n**Canal:** {self.channel.mention}\n**Hora:** <t:{int(datetime.now().timestamp())}:F>",
                    color=0x00E5A8
                )
                
                if self.modal.contenido.value:
                    log_embed.add_field(
                        name="Contenido",
                        value=self.modal.contenido.value[:200] + ("..." if len(self.modal.contenido.value) > 200 else ""),
                        inline=False
                    )
                
                # Usar el sistema de logs detallado
                if 'logs' in CANALES_BOT and GUILD_ID:
                    guild = interaction.client.get_guild(GUILD_ID)
                    if guild:
                        canal_logs = guild.get_channel(CANALES_BOT['logs'])
                        if canal_logs:
                            await canal_logs.send(embed=log_embed)
            except Exception as e:
                log.error(f"Error enviando log detallado: {e}")
                # Fallback al sistema simple
                try:
                    await log_accion("Mensaje Publicado por Staff", interaction.user.display_name, f"Canal: {self.channel.name}")
                except:
                    pass
            
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error al publicar mensaje: {str(e)}",
                embed=None,
                view=None
            )
    
    @ui.button(label="Cancelar", style=nextcord.ButtonStyle.danger)
    async def cancel_button(self, button: ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(
            content="❌ Publicación cancelada.",
            embed=None,
            view=None
        )

# Modal de configuración adicional eliminado para simplificar

# Vista eliminada - no se usa en el nuevo sistema

# Vista eliminada - no se usa en el nuevo sistema

# ========== SISTEMA AUTOMÁTICO DE CANALES ==========

# Diccionario para almacenar canales automáticamente
CANALES_BOT = {}

# Métodos de pago actualizados
METODOS_PAGO = [
    "💳 **Transferencia Bancaria**",
    "📱 **Klar** - Transferencia instantánea",
    "🟣 **Nu** - Transferencia bancaria",
    "🟡 **Bybit** - Criptomonedas",
    "🟠 **Binance** - Criptomonedas",
    "🟢 **Mercado Pago** - Transferencia",
    "💸 **Efectivo** - En persona"
]

async def actualizar_canales_bot(guild):
    """Actualizar automáticamente la lista de canales del bot"""
    global CANALES_BOT
    
    try:
        # Obtener todos los canales del servidor
        canales_texto = [channel for channel in guild.text_channels if channel.type == nextcord.ChannelType.text]
        
        # Categorizar canales automáticamente
        for canal in canales_texto:
            nombre = canal.name.lower()
            
            # Detectar tipo de canal por nombre
            if any(palabra in nombre for palabra in ['anuncio', 'announcement', 'general', 'main']):
                CANALES_BOT['anuncios'] = canal.id
            elif any(palabra in nombre for palabra in ['log', 'logs', 'admin', 'mod']):
                CANALES_BOT['logs'] = canal.id
            elif any(palabra in nombre for palabra in ['ticket', 'tickets', 'soporte', 'support']):
                CANALES_BOT['tickets'] = canal.id
            elif any(palabra in nombre for palabra in ['reglas', 'rules', 'info', 'informacion']):
                CANALES_BOT['reglas'] = canal.id
            elif any(palabra in nombre for palabra in ['bienvenida', 'welcome', 'entrada']):
                CANALES_BOT['bienvenida'] = canal.id
        
        # Si no se detectaron automáticamente, usar canales por defecto
        if 'anuncios' not in CANALES_BOT and canales_texto:
            CANALES_BOT['anuncios'] = canales_texto[0].id
        
        log.info(f"Canales del bot actualizados: {CANALES_BOT}")
        
        # Crear mensajes automáticos en cada canal (desactivado por ahora)
        # await crear_mensajes_automaticos(guild)
        
    except Exception as e:
        log.error(f"Error actualizando canales: {e}")

async def crear_mensajes_automaticos(guild):
    """Crear mensajes automáticos en canales específicos"""
    try:
        # Canal de reglas
        if 'reglas' in CANALES_BOT:
            canal_reglas = guild.get_channel(CANALES_BOT['reglas'])
            if canal_reglas:
                embed_reglas = nextcord.Embed(
                    title="📜 **Reglas del Servidor**",
                    description="Lee y respeta estas reglas para mantener un ambiente agradable:",
                    color=0x00FF00,
                    timestamp=nextcord.utils.utcnow()
                )
                embed_reglas.add_field(
                    name="1️⃣ **Respeto**",
                    value="Trata a todos con respeto y cortesía",
        inline=False
    )
                embed_reglas.add_field(
                    name="2️⃣ **No Spam**",
                    value="No envíes mensajes repetitivos o innecesarios",
        inline=False
    )
                embed_reglas.add_field(
                    name="3️⃣ **Lenguaje Apropiado**",
                    value="Mantén un lenguaje respetuoso y apropiado",
        inline=False
    )
                embed_reglas.add_field(
                    name="4️⃣ **Canales Correctos**",
                    value="Usa los canales para su propósito específico",
        inline=False
    )
                embed_reglas.set_footer(text="ONZA Bot • Reglas del Servidor")
                
                        # Limpiar mensajes antiguos y enviar nuevo
        try:
            await canal_reglas.purge(limit=100)
            await canal_reglas.send(embed=embed_reglas)
        except Exception as e:
            log.error(f"Error en canal reglas: {e}")
        
        # Canal de bienvenida
        if 'bienvenida' in CANALES_BOT:
            canal_bienvenida = guild.get_channel(CANALES_BOT['bienvenida'])
            if canal_bienvenida:
                embed_bienvenida = nextcord.Embed(
                    title="🎉 **¡Bienvenido a ONZA!**",
                    description="Gracias por unirte a nuestro servidor. Aquí encontrarás todo lo que necesitas:",
                    color=0x00FFFF,
                    timestamp=nextcord.utils.utcnow()
                )
                embed_bienvenida.add_field(
                    name="🎫 **Soporte**",
                    value="Abre un ticket en <#{}> si necesitas ayuda".format(CANALES_BOT.get('tickets', 'canal-tickets')),
                    inline=False
                )
                embed_bienvenida.add_field(
                    name="📋 **Información**",
                    value="Consulta las reglas en <#{}>".format(CANALES_BOT.get('reglas', 'canal-reglas')),
                    inline=False
                )
                embed_bienvenida.add_field(
                    name="💳 **Métodos de Pago**",
                    value="Usa `/metodos_pago` para ver opciones disponibles",
                    inline=False
                )
                embed_bienvenida.set_footer(text="ONZA Bot • Bienvenida")
                
                # Limpiar mensajes antiguos y enviar nuevo
                try:
                    await canal_bienvenida.purge(limit=100)
                    await canal_bienvenida.send(embed=embed_bienvenida)
                except Exception as e:
                    log.error(f"Error en canal bienvenida: {e}")
        
        # Canal de tickets
        if 'tickets' in CANALES_BOT:
            canal_tickets = guild.get_channel(CANALES_BOT['tickets'])
            if canal_tickets:
                embed_tickets = nextcord.Embed(
                    title="🎫 **Sistema de Tickets**",
                    description="¿Necesitas ayuda? El sistema de tickets funciona a través del panel que ya está publicado en este canal:",
                    color=0xFFA500,
                    timestamp=nextcord.utils.utcnow()
                )
                embed_tickets.add_field(
                    name="📋 **Panel de Tickets**",
                    value="• **Ubicación:** Panel publicado en este canal\n• **Uso:** Selecciona el servicio deseado del menú desplegable\n• **Acceso:** Solo usuarios pueden usar el panel (staff no puede abrir tickets)",
                    inline=False
                )
                embed_tickets.add_field(
                    name="🔧 **Información Adicional**",
                    value="• **Servicios:** Usa `/servicios` para ver qué ofrecemos\n• **Pagos:** Usa `/metodos_pago` para ver opciones de pago",
                    inline=False
                )
                embed_tickets.add_field(
                    name="⚠️ **Importante**",
                    value="• El comando `/panel` es solo para staff\n• Los usuarios deben usar el panel ya publicado\n• Se creará un ticket privado automáticamente",
                    inline=False
                )
                embed_tickets.set_footer(text="ONZA Bot • Sistema de Tickets")
                
                # Limpiar mensajes antiguos y enviar nuevo
                try:
                    await canal_tickets.purge(limit=100)
                    await canal_tickets.send(embed=embed_tickets)
                except Exception as e:
                    log.error(f"Error en canal tickets: {e}")
        
        log.info("Mensajes automáticos creados en canales")
        
    except Exception as e:
        log.error(f"Error creando mensajes automáticos: {e}")

async def log_accion(accion: str, usuario: str, detalles: str = ""):
    """Registrar acción en el canal de logs"""
    try:
        if 'logs' in CANALES_BOT and GUILD_ID:
            guild = bot.get_guild(GUILD_ID)
            if guild:
                canal_logs = guild.get_channel(CANALES_BOT['logs'])
                if canal_logs:
                    embed_log = nextcord.Embed(
                        title=f"📋 **Log: {accion}**",
                        description=f"**Usuario:** {usuario}\n**Detalles:** {detalles}",
                        color=0x00FFFF,
                        timestamp=nextcord.utils.utcnow()
                    )
                    embed_log.set_footer(text="ONZA Bot • Sistema de Logs")
                    await canal_logs.send(embed=embed_log)
    except Exception as e:
        log.error(f"Error enviando log: {e}")

# ========== COMANDO ACTUALIZAR CANALES ==========

@bot.slash_command(name="actualizar_canales", description="Actualizar lista de canales del bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def actualizar_canales(interaction: nextcord.Interaction):
    """Actualizar automáticamente la lista de canales"""
    if not isinstance(interaction.user, nextcord.Member) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo los administradores pueden usar este comando.", ephemeral=True)
        return
    
    try:
        await actualizar_canales_bot(interaction.guild)
        
        embed = nextcord.Embed(
            title="✅ **Canales Actualizados**",
            description="La lista de canales ha sido actualizada automáticamente:",
            color=0x00FF00,
            timestamp=nextcord.utils.utcnow()
        )
        
        for tipo, canal_id in CANALES_BOT.items():
            canal = interaction.guild.get_channel(canal_id)
            if canal:
                embed.add_field(
                    name=f"📢 {tipo.title()}",
                    value=f"{canal.mention} (`{canal_id}`)",
                    inline=False
                )
        
        embed.set_footer(text="ONZA Bot • Actualización Automática")
        
        await interaction.response.send_message(
            "✅ **Canales actualizados automáticamente**",
            embed=embed,
            ephemeral=True
        )
        
        # Log de la acción
        await log_accion("Canales Actualizados", interaction.user.display_name, f"Total canales: {len(CANALES_BOT)}")
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ **Error al actualizar:** {str(e)}",
            ephemeral=True
        )

# ========== COMANDO SINCRONIZAR COMANDOS ==========

@bot.slash_command(name="sync_commands", description="Sincronizar comandos slash (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def sync_commands(interaction: nextcord.Interaction):
    """Forzar sincronización de comandos slash"""
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        await bot.sync_all_application_commands()
        # Mostrar información de comandos
        commands_count = len(bot.application_commands)
        commands_list = [f"• `/{cmd.name}`" for cmd in bot.application_commands[:10]]
        commands_text = "\n".join(commands_list)
        if commands_count > 10:
            commands_text += f"\n... y {commands_count - 10} más"
        
        success_embed = nextcord.Embed(
            title="✅ **Comandos Sincronizados**",
            description=f"Sincronizados **{commands_count}** comandos correctamente.",
            color=0x00FF00,
            timestamp=nextcord.utils.utcnow()
        )
        
        success_embed.add_field(
            name="📋 **Comandos registrados**",
            value=commands_text,
            inline=False
        )
        
        success_embed.add_field(
            name="⏰ **Tiempo de aparición**",
            value="• **5-15 minutos**: Tiempo normal\n• **Hasta 1 hora**: En casos excepcionales",
            inline=False
        )
        
        success_embed.add_field(
            name="🔧 **Si no aparecen**",
            value="1. Espera unos minutos\n2. Reinicia Discord\n3. Verifica permisos del bot\n4. Usa este comando nuevamente",
            inline=False
        )
        
        success_embed.set_footer(text="ONZA Bot • Sistema de Sincronización")
        
        await interaction.followup.send(embed=success_embed, ephemeral=True)
        log.info(f"Comandos sincronizados manualmente por {interaction.user.display_name}")
    except Exception as e:
        error_embed = nextcord.Embed(
            title="❌ **Error de Sincronización**",
            description=f"Error al sincronizar comandos: {str(e)}",
            color=0xFF0000,
            timestamp=nextcord.utils.utcnow()
        )
        
        error_embed.add_field(
            name="🔧 **Soluciones**",
            value="1. Verifica que el bot tenga permisos de administrador\n2. Intenta nuevamente en unos minutos\n3. Contacta al desarrollador si persiste",
            inline=False
        )
        
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        log.error(f"Error en sincronización manual: {e}")

# ========== COMANDO REINICIAR RENDER ==========

@bot.slash_command(name="reiniciar_render", description="Reiniciar el servicio de Render (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def reiniciar_render(interaction: nextcord.Interaction):
    """Reiniciar el servicio de Render desde Discord"""
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Mostrar embed informativo
        info_embed = nextcord.Embed(
            title="🔄 **Reinicio de Render**",
            description="Para reiniciar el servicio de Render:",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        
        info_embed.add_field(
            name="📋 **Pasos para reiniciar**",
            value="1. Ve a [Render Dashboard](https://dashboard.render.com)\n2. Selecciona tu servicio\n3. Haz clic en 'Manual Deploy'\n4. Selecciona 'Deploy latest commit'",
            inline=False
        )
        
        info_embed.add_field(
            name="⏰ **Tiempo estimado**",
            value="El reinicio tomará 1-3 minutos",
            inline=False
        )
        
        info_embed.add_field(
            name="🔧 **Alternativa**",
            value="También puedes usar el botón 'Restart' en el dashboard de Render",
            inline=False
        )
        
        info_embed.set_footer(text="ONZA Bot • Sistema de Reinicio")
        
        await interaction.followup.send(embed=info_embed, ephemeral=True)
        
        # Log de la acción
        await log_accion(
            "Render Reinicio Consultado",
            interaction.user.display_name,
            "Usuario consultó información de reinicio"
        )
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        log.error(f"Error en reiniciar_render: {e}")

# ========== COMANDO OBTENER ID DE CANAL ==========

@bot.slash_command(name="canal_id", description="Obtener ID de un canal", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def canal_id(interaction: nextcord.Interaction,
                   canal: nextcord.TextChannel = nextcord.SlashOption(description="Canal del cual obtener ID", required=True)):
    """Obtener el ID de un canal específico"""
    embed = nextcord.Embed(
        title="🆔 **ID del Canal**",
        description=f"**Canal:** {canal.mention}\n**ID:** `{canal.id}`",
        color=0x00E5A8,
        timestamp=nextcord.utils.utcnow()
    )
    
    embed.add_field(
        name="📋 **Cómo usar**",
        value="Copia este ID y úsalo en `/configurar_canales`",
        inline=False
    )
    
    embed.set_footer(text="ONZA Bot • Información de Canal")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Log de la acción
    await log_accion("ID de Canal Consultado", interaction.user.display_name, f"Canal: {canal.name}")

# ========== MODAL PARA BANEO ==========

class BanModal(nextcord.ui.Modal):
    """Modal para banear usuarios"""
    def __init__(self):
        super().__init__(title="🔨 Banear Usuario", timeout=300)
        
        # Campo para ID del usuario
        self.user_id_input = nextcord.ui.TextInput(
            label="ID del Usuario",
            placeholder="Ingresa el ID del usuario a banear",
            required=True,
            max_length=20
        )
        self.add_item(self.user_id_input)
        
        # Campo para razón del baneo
        self.reason_input = nextcord.ui.TextInput(
            label="Razón del Baneo",
            placeholder="Ingresa la razón del baneo (opcional)",
            required=False,
            max_length=500,
            style=nextcord.TextInputStyle.paragraph
        )
        self.add_item(self.reason_input)
    
    async def callback(self, interaction: nextcord.Interaction):
        """Procesar el baneo del usuario"""
        try:
            # Obtener ID del usuario
            user_id = int(self.user_id_input.value.strip())
            
            # Obtener razón (o usar una por defecto)
            reason = self.reason_input.value.strip() or "Sin razón especificada"
            
            # Obtener el usuario
            try:
                user = await interaction.client.fetch_user(user_id)
            except nextcord.NotFound:
                await interaction.response.send_message("❌ Usuario no encontrado.", ephemeral=True)
                return
            except nextcord.HTTPException:
                await interaction.response.send_message("❌ Error al obtener información del usuario.", ephemeral=True)
                return
            
            # Verificar que no sea el bot
            if user.id == interaction.client.user.id:
                await interaction.response.send_message("❌ No puedes banear al bot.", ephemeral=True)
                return
            
            # Verificar que no sea el usuario que ejecuta el comando
            if user.id == interaction.user.id:
                await interaction.response.send_message("❌ No puedes banearte a ti mismo.", ephemeral=True)
                return
            
            # Verificar que el usuario esté en el servidor
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message("❌ El usuario no está en este servidor.", ephemeral=True)
                return
            
            # Verificar que el usuario no tenga un rol más alto
            if member.top_role >= interaction.user.top_role:
                await interaction.response.send_message("❌ No puedes banear a un usuario con un rol igual o superior al tuyo.", ephemeral=True)
                return
            
            # Confirmar baneo
            confirm_embed = nextcord.Embed(
                title="⚠️ **Confirmar Baneo**",
                description=f"¿Estás seguro de que quieres banear a **{user.display_name}**?",
                color=0xFF0000,
                timestamp=nextcord.utils.utcnow()
            )
            
            confirm_embed.add_field(
                name="👤 **Usuario**",
                value=f"{user.mention} ({user.display_name})",
                inline=False
            )
            
            confirm_embed.add_field(
                name="📝 **Razón**",
                value=reason,
                inline=False
            )
            
            confirm_embed.set_thumbnail(url=user.display_avatar.url)
            confirm_embed.set_footer(text="Esta acción no se puede deshacer")
            
            # Crear vista de confirmación
            confirm_view = BanConfirmView(user, reason)
            
            await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ ID de usuario inválido. Debe ser un número.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error procesando el baneo: {str(e)}", ephemeral=True)
            log.error(f"Error en modal de baneo: {e}")

class BanConfirmView(nextcord.ui.View):
    """Vista de confirmación para baneo"""
    def __init__(self, user, reason):
        super().__init__(timeout=60)
        self.user = user
        self.reason = reason
    
    @nextcord.ui.button(label="✅ Confirmar Baneo", style=nextcord.ButtonStyle.danger, emoji="🔨")
    async def confirm_ban(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Confirmar el baneo"""
        try:
            # Ejecutar el baneo
            await interaction.guild.ban(
                self.user,
                reason=f"Baneado por {interaction.user.display_name}: {self.reason}",
                delete_message_days=0
            )
            
            # Embed de confirmación
            success_embed = nextcord.Embed(
                title="✅ **Usuario Baneado**",
                description=f"**{self.user.display_name}** ha sido baneado del servidor.",
                color=0x00FF00,
                timestamp=nextcord.utils.utcnow()
            )
            
            success_embed.add_field(
                name="👤 **Usuario**",
                value=f"{self.user.mention} ({self.user.display_name})",
                inline=False
            )
            
            success_embed.add_field(
                name="📝 **Razón**",
                value=self.reason,
                inline=False
            )
            
            success_embed.add_field(
                name="👮 **Moderador**",
                value=interaction.user.mention,
                inline=False
            )
            
            success_embed.set_thumbnail(url=self.user.display_avatar.url)
            success_embed.set_footer(text="ONZA Bot • Sistema de Moderación")
            
            await interaction.response.edit_message(embed=success_embed, view=None)
            
            # Log de la acción
            await log_accion(
                "Usuario Baneado",
                interaction.user.display_name,
                f"Usuario: {self.user.display_name} ({self.user.id}), Razón: {self.reason}"
            )
            
            log.info(f"Usuario {self.user.display_name} ({self.user.id}) baneado por {interaction.user.display_name}")
            
        except nextcord.Forbidden:
            await interaction.response.edit_message(
                content="❌ No tengo permisos para banear a este usuario.",
                embed=None,
                view=None
            )
        except nextcord.HTTPException as e:
            await interaction.response.edit_message(
                content=f"❌ Error al banear usuario: {str(e)}",
                embed=None,
                view=None
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error inesperado: {str(e)}",
                embed=None,
                view=None
            )
            log.error(f"Error baneando usuario: {e}")
    
    @nextcord.ui.button(label="❌ Cancelar", style=nextcord.ButtonStyle.secondary)
    async def cancel_ban(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        """Cancelar el baneo"""
        cancel_embed = nextcord.Embed(
            title="❌ **Baneo Cancelado**",
            description="El baneo ha sido cancelado.",
            color=0xFFA500,
            timestamp=nextcord.utils.utcnow()
        )
        
        await interaction.response.edit_message(embed=cancel_embed, view=None)

# ========== COMANDO BANEAR USUARIO ==========

@bot.slash_command(name="banear", description="Banear un usuario del servidor (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def banear_usuario(interaction: nextcord.Interaction):
    """Banear un usuario del servidor"""
    # Verificar que sea staff
    if not is_staff(interaction.user):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return
    
    # Verificar permisos del bot
    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message("❌ No tengo permisos para banear usuarios.", ephemeral=True)
        return
    
    # Mostrar modal
    modal = BanModal()
    await interaction.response.send_modal(modal)

# ========== TAREAS DE FONDO ==========

@tasks.loop(hours=24)
async def maintenance_loop():
    """Tarea de mantenimiento diario"""
    try:
        log.info("Ejecutando tarea de mantenimiento diario...")
        # Tareas ligeras de mantenimiento
        # - Verificar conexión del bot
        # - Log de estado
    except Exception as e:
        log.error(f"Error en maintenance_loop: {e}")

# ========== MANEJO DE ERRORES ==========

@bot.event
async def on_command_error(ctx, error):
    """Manejar errores de comandos"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para usar este comando.")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Falta argumento requerido: {error.param}")
        return
    
    log.error(f"Error en comando {ctx.command}: {error}")
    await ctx.send("❌ Ocurrió un error al ejecutar el comando.")

@bot.event
async def on_error(event, *args, **kwargs):
    """Manejar errores generales"""
    log.error(f"Error en evento {event}: {args} {kwargs}")

# ========== FUNCIÓN PRINCIPAL ==========

async def main():
    """Función principal del bot"""
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN no configurado en variables de entorno")
        return
    
    try:
        log.info("Iniciando ONZA Bot...")
        log.info(f"Versión: 3.0 Optimizada")
        log.info(f"Python: {sys.version}")
        log.info(f"Nextcord: {nextcord.__version__}")
        
        # Iniciar servidor web para keep-alive
        webserver.keep_alive()
        log.info("🌐 Servidor web keep-alive iniciado")
        
        # Iniciar tareas en segundo plano
        maintenance_loop.start()
        
        log.info("Tareas en segundo plano iniciadas")
        
        # Conectar bot
        await bot.start(DISCORD_TOKEN)
        
    except KeyboardInterrupt:
        log.info("Recibida señal de interrupción, cerrando bot...")
    except Exception as e:
        log.error(f"Error iniciando bot: {e}")
        log.error(f"Traceback completo: {traceback.format_exc()}")
    finally:
        # Limpiar tareas
        try:
            maintenance_loop.cancel()
            log.info("Tareas en segundo plano detenidas")
        except:
            pass
        
        # Cerrar conexiones de base de datos
        try:
            await bot.close()
            log.info("Bot cerrado correctamente")
        except:
            pass

def signal_handler(signum, frame):
    """Manejar señales del sistema"""
    log.info(f"Recibida señal {signum}, cerrando bot...")
    sys.exit(0)

if __name__ == "__main__":
    # Configurar manejo de señales
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Importar traceback para mejor debugging
    import traceback
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
