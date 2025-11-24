"""
Manejo de mensajes interactivos del bot
"""

import logging
from typing import Optional

import nextcord
from nextcord.ext import commands

from config import *
from utils import log
from commands.tickets import SimpleTicketView

async def actualizar_mensajes_interactivos(bot: commands.Bot):
    """Actualizar automáticamente todos los mensajes interactivos del servidor"""
    try:
        log.info("Iniciando actualización de mensajes interactivos...")
        
        from config import TICKET_CHANNEL_ID
        
        # Buscar y actualizar el panel de tickets en todos los servidores
        for guild in bot.guilds:
            # Buscar canal de tickets por ID o por nombre
            canal_tickets = None
            
            if TICKET_CHANNEL_ID:
                canal_tickets = guild.get_channel(TICKET_CHANNEL_ID)
            
            # Si no se encuentra por ID, buscar por nombre
            if not canal_tickets:
                for channel in guild.channels:
                    if isinstance(channel, nextcord.TextChannel):
                        channel_name_lower = channel.name.lower()
                        if 'tickets' in channel_name_lower or 'ticket' in channel_name_lower:
                            canal_tickets = channel
                            break
            
            if canal_tickets:
                log.info(f"Canal de tickets encontrado en {guild.name}: {canal_tickets.name}")
                await actualizar_panel_tickets(canal_tickets)
            else:
                log.warning(f"No se encontró el canal de tickets en {guild.name}")
        
        log.info("Mensajes interactivos actualizados correctamente")
        
    except Exception as e:
        log.error(f"Error actualizando mensajes interactivos: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")

async def actualizar_panel_tickets(canal: nextcord.TextChannel):
    """Actualizar el panel de tickets en el canal especificado"""
    try:
        # Limpiar mensajes antiguos del panel
        async for message in canal.history(limit=50):
            # Buscar mensajes que contengan el panel de tickets
            if (message.author == canal.guild.me and 
                message.embeds and 
                any("🎫 Soporte" in embed.title for embed in message.embeds)):
                await message.delete()
                break
        
        # Crear y publicar el nuevo panel
        view = SimpleTicketView()
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
        log.info("Panel de tickets actualizado correctamente")
        
    except Exception as e:
        log.error(f"Error actualizando panel de tickets: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")
