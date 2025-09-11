"""
Manejo de canales del bot
"""

import logging
from typing import Dict, Optional

import nextcord
from nextcord.ext import commands

from config import *
from utils import log

async def actualizar_canales_bot(guild: nextcord.Guild):
    """Actualizar canales del bot automáticamente"""
    try:
        log.info("Iniciando actualización de canales del bot...")
        
        # Buscar canales por nombre
        channels_found = {}
        
        for channel in guild.channels:
            if isinstance(channel, nextcord.TextChannel):
                channel_name_lower = channel.name.lower()
                
                # Mapear canales por nombre
                if 'tickets' in channel_name_lower or 'ticket' in channel_name_lower:
                    channels_found['tickets'] = channel.id
                elif 'reglas' in channel_name_lower or 'rules' in channel_name_lower:
                    channels_found['reglas'] = channel.id
                elif 'bienvenida' in channel_name_lower or 'welcome' in channel_name_lower:
                    channels_found['bienvenida'] = channel.id
                elif 'como-comprar' in channel_name_lower or 'how-to-buy' in channel_name_lower:
                    channels_found['como_comprar'] = channel.id
                elif 'catalogo' in channel_name_lower or 'catalog' in channel_name_lower:
                    channels_found['catalogo'] = channel.id
                elif 'metodos-pago' in channel_name_lower or 'payment' in channel_name_lower:
                    channels_found['metodos_pago'] = channel.id
                elif 'reseñas' in channel_name_lower or 'reviews' in channel_name_lower:
                    channels_found['reseñas'] = channel.id
                elif 'logs' in channel_name_lower and 'ticket' in channel_name_lower:
                    channels_found['tickets_log'] = channel.id
                elif 'logs' in channel_name_lower and 'payment' in channel_name_lower:
                    channels_found['payments_log'] = channel.id
        
        # Actualizar CANALES_BOT
        from config import CANALES_BOT
        CANALES_BOT.update(channels_found)
        
        log.info(f"Canales encontrados: {channels_found}")
        log.info("Canales del bot actualizados correctamente")
        
    except Exception as e:
        log.error(f"Error actualizando canales del bot: {e}")
        import traceback
        log.error(f"Traceback completo: {traceback.format_exc()}")

def get_channel_by_name(guild: nextcord.Guild, name: str) -> Optional[nextcord.TextChannel]:
    """Obtener canal por nombre"""
    try:
        for channel in guild.channels:
            if isinstance(channel, nextcord.TextChannel) and name.lower() in channel.name.lower():
                return channel
        return None
    except Exception as e:
        log.error(f"Error obteniendo canal {name}: {e}")
        return None

def get_category_by_name(guild: nextcord.Guild, name: str) -> Optional[nextcord.CategoryChannel]:
    """Obtener categoría por nombre"""
    try:
        for category in guild.categories:
            if name.lower() in category.name.lower():
                return category
        return None
    except Exception as e:
        log.error(f"Error obteniendo categoría {name}: {e}")
        return None
