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

async def actualizar_mensajes_interactivos(guild: nextcord.Guild):
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
