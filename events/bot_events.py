"""
Eventos principales del bot ONZA
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, db_execute, db_query_one, db_query_all
from i18n import t, get_user_lang

class BotEvents:
    """Maneja los eventos principales del bot"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # Evento on_ready movido a bot.py para evitar duplicación
    
    async def on_guild_join(self, guild: nextcord.Guild):
        """Evento cuando el bot se une a un servidor"""
        log.info(f"Bot unido a servidor: {guild.name} (ID: {guild.id})")
    
    async def on_member_join(self, member: nextcord.Member):
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
                # Crear embed de bienvenida
                embed = nextcord.Embed(
                    title="🎉 ¡Bienvenido a ONZA! 🎉",
                    description=f"¡Hola {member.mention}! Te damos la bienvenida a nuestro servidor.",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                # Agregar información útil
                embed.add_field(
                    name="🛒 ¿Cómo comprar?",
                    value=f"Para realizar compras, visita el canal {member.guild.get_channel(HOW_TO_BUY_CHANNEL_ID).mention if member.guild.get_channel(HOW_TO_BUY_CHANNEL_ID) else '#como-comprar'}",
                    inline=False
                )
                
                embed.add_field(
                    name="🎫 ¿Necesitas ayuda?",
                    value="Abre un ticket en el canal de tickets para recibir soporte personalizado.",
                    inline=False
                )
                
                embed.set_footer(text=f"{BRAND_NAME} • ¡Disfruta tu estadía!")
                
                await welcome_channel.send(embed=embed)
                
        except Exception as e:
            log.error(f"Error en evento on_member_join: {e}")
    
    async def on_message(self, message: nextcord.Message):
        """Evento cuando se recibe un mensaje"""
        # Ignorar mensajes del bot
        if message.author == self.bot.user:
            return
        
        # Aplicar moderación automática
        try:
            from .moderation_events import auto_mod
            if auto_mod:
                should_delete = await auto_mod.check_message(message)
                if should_delete:
                    return  # El mensaje ya fue manejado por la moderación
        except Exception as e:
            log.error(f"Error en moderación automática: {e}")
        
        # Procesar comandos
        await self.bot.process_commands(message)
    
    async def on_interaction(self, interaction: nextcord.Interaction):
        """Evento cuando hay una interacción"""
        try:
            # Log de interacciones
            if interaction.type == nextcord.InteractionType.application_command:
                log.info(f"Comando usado: /{interaction.data.get('name', 'unknown')} por {interaction.user.display_name}")
        except Exception as e:
            log.error(f"Error en evento on_interaction: {e}")
