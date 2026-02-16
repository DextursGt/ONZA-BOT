"""
Manejo de mensajes interactivos del bot
"""


import nextcord
from nextcord.ext import commands

from config import *
from utils import log

async def actualizar_mensajes_interactivos(bot_or_guild):
    """Actualizar automáticamente todos los mensajes interactivos del servidor
    Acepta tanto bot como guild para compatibilidad
    """
    try:
        log.info("Iniciando actualización de mensajes interactivos...")
        
        # Determinar si recibimos bot o guild
        if isinstance(bot_or_guild, commands.Bot):
            # Si es bot, iterar sobre todos los guilds
            guilds = bot_or_guild.guilds
        else:
            # Si es guild, usar solo ese
            guilds = [bot_or_guild]
        
        from config import TICKET_CHANNEL_ID
        
        # ID del canal específico donde debe ir el panel
        TARGET_TICKET_CHANNEL_ID = 1408132580259270766
        
        # Intentar usar CANALES_BOT si existe
        try:
            from config import CANALES_BOT
            use_canales_bot = True
        except (ImportError, AttributeError):
            use_canales_bot = False
        
        # Buscar y actualizar el panel de tickets
        for guild in guilds:
            canal_tickets = None
            
            # PRIMERO: Intentar con el canal específico (1408132580259270766)
            try:
                canal_tickets = guild.get_channel(TARGET_TICKET_CHANNEL_ID)
                if canal_tickets:
                    log.info(f"✅ Canal encontrado por ID específico: {canal_tickets.name} (ID: {TARGET_TICKET_CHANNEL_ID})")
            except Exception as e:
                log.warning(f"Error obteniendo canal por ID específico: {e}")
            
            # SEGUNDO: Intentar con CANALES_BOT si existe
            if not canal_tickets and use_canales_bot:
                try:
                    canal_tickets = guild.get_channel(CANALES_BOT.get('tickets'))
                    if canal_tickets:
                        log.info(f"Canal encontrado por CANALES_BOT: {canal_tickets.name}")
                except:
                    pass
            
            # TERCERO: Usar TICKET_CHANNEL_ID de config
            if not canal_tickets and TICKET_CHANNEL_ID:
                try:
                    canal_tickets = guild.get_channel(TICKET_CHANNEL_ID)
                    if canal_tickets:
                        log.info(f"Canal encontrado por TICKET_CHANNEL_ID: {canal_tickets.name} (ID: {TICKET_CHANNEL_ID})")
                except Exception as e:
                    log.warning(f"Error obteniendo canal por TICKET_CHANNEL_ID: {e}")
            
            # CUARTO: Buscar por nombre como último recurso
            if not canal_tickets:
                log.info(f"Buscando canal de tickets por nombre en {guild.name}...")
                for channel in guild.channels:
                    if isinstance(channel, nextcord.TextChannel):
                        channel_name_lower = channel.name.lower()
                        if 'tickets' in channel_name_lower or 'ticket' in channel_name_lower:
                            canal_tickets = channel
                            log.info(f"Canal encontrado por nombre: {canal_tickets.name} (ID: {canal_tickets.id})")
                            break
            
            if canal_tickets:
                log.info(f"Canal de tickets encontrado en {guild.name}: {canal_tickets.name} (ID: {canal_tickets.id})")
                # Pasar el bot si está disponible
                bot_instance = bot_or_guild if isinstance(bot_or_guild, commands.Bot) else None
                await actualizar_panel_tickets(canal_tickets, bot_instance)
            else:
                log.warning(f"No se encontró el canal de tickets en {guild.name}. TICKET_CHANNEL_ID={TICKET_CHANNEL_ID}")
        
        log.info("Mensajes interactivos actualizados correctamente")
        
    except Exception as e:
        log.error(f"Error actualizando mensajes interactivos: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")

async def actualizar_panel_tickets(canal: nextcord.TextChannel, bot=None):
    """Actualizar el panel de tickets en el canal especificado"""
    try:
        # Limpiar mensajes antiguos del panel
        async for message in canal.history(limit=50):
            # Buscar mensajes que contengan el panel de tickets
            if (message.author == canal.guild.me and 
                message.embeds and 
                any("🎫 Soporte" in embed.title or "🎫 Panel" in embed.title for embed in message.embeds)):
                await message.delete()
                break
        
        # Importar SimpleTicketView y obtener la instancia del cog
        from commands.tickets import SimpleTicketView
        
        # Obtener la instancia del cog de tickets del bot
        ticket_cog = None
        if bot:
            ticket_cog = bot.get_cog('SimpleTicketCommands')
            if ticket_cog:
                log.info("✅ Instancia de SimpleTicketCommands encontrada")
            else:
                log.warning("⚠️ No se encontró SimpleTicketCommands cog")
        
        # Crear y publicar el nuevo panel
        view = SimpleTicketView(ticket_cog)
        embed = nextcord.Embed(
            title=f"🎫 Panel de Tickets - {BRAND_NAME}",
            description="**¡Bienvenido a nuestro sistema de tickets!**\n\n"
                       "Selecciona el tipo de servicio que necesitas y crearemos un ticket privado para ti.\n"
                       "Un miembro del staff te atenderá pronto.\n\n"
                       "━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        embed.add_field(
            name="📋 **Servicios Disponibles**",
            value="• **Discord Nitro/Basic:** Suscripciones premium\n• **Spotify:** Individual y Duo\n• **YouTube Premium:** Acceso sin anuncios\n• **Crunchyroll:** Anime y manga\n• **Robux:** Moneda virtual de Roblox\n• **Accesorios Discord:** Decoraciones y themes",
            inline=False
        )
        embed.add_field(
            name="🕐 **Horario de Atención**",
            value="**10:00 AM - 10:00 PM** (Horario de México)",
            inline=False
        )
        embed.set_footer(text=f"{BRAND_NAME} • Sistema de Tickets")
        
        await canal.send(embed=embed, view=view)
        log.info(f"✅ Panel de tickets actualizado correctamente en {canal.name} (ID: {canal.id})")
        
    except Exception as e:
        log.error(f"Error actualizando panel de tickets: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")
