"""
Sistema de moderación automática para ONZA Bot
Versión: 3.0
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, db_execute, db_query_one

class AutoModeration:
    """Sistema de moderación automática"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_warnings = {}  # {user_id: [timestamps]}
        self.user_messages = {}  # {user_id: [message_timestamps]}
        
        # Configuración de moderación
        self.max_warnings = 3
        self.warning_cooldown = 300  # 5 minutos
        self.spam_threshold = 5  # 5 mensajes
        self.spam_timeframe = 10  # en 10 segundos
        
        # Links permitidos (solo de ONZA)
        self.allowed_domains = [
            'onza.com',
            'onza.mx', 
            'discord.gg/onza',
            'discord.com/invite/onza',
            't.me/onza',
            'telegram.me/onza'
        ]
        
        # Palabras prohibidas (spam/raid)
        self.banned_words = [
            'discord.gg/',
            'discord.com/invite/',
            't.me/',
            'telegram.me/',
            'youtube.com/watch',
            'youtu.be/',
            'bit.ly/',
            'tinyurl.com/',
            'discord.gg/',
            'nitro',
            'free nitro',
            'steam',
            'steamcommunity.com',
            'steamdb.info'
        ]
    
    async def check_message(self, message: nextcord.Message) -> bool:
        """
        Verifica un mensaje y aplica moderación automática
        Retorna True si el mensaje debe ser eliminado
        """
        try:
            # Ignorar staff y bots
            if is_staff(message.author) or message.author.bot:
                return False
            
            # Verificar spam
            if await self._check_spam(message):
                await self._handle_spam(message)
                return True
            
            # Verificar links no permitidos
            if await self._check_links(message):
                await self._handle_links(message)
                return True
            
            # Verificar palabras prohibidas
            if await self._check_banned_words(message):
                await self._handle_banned_words(message)
                return True
            
            # Verificar raids (múltiples usuarios nuevos)
            if await self._check_raid(message):
                await self._handle_raid(message)
                return True
            
            return False
            
        except Exception as e:
            log.error(f"Error en moderación automática: {e}")
            return False
    
    async def _check_spam(self, message: nextcord.Message) -> bool:
        """Verifica si el usuario está haciendo spam"""
        user_id = message.author.id
        now = datetime.now(timezone.utc)
        
        # Inicializar si es nuevo usuario
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
        
        # Agregar mensaje actual
        self.user_messages[user_id].append(now)
        
        # Limpiar mensajes antiguos
        cutoff = now - timedelta(seconds=self.spam_timeframe)
        self.user_messages[user_id] = [
            msg_time for msg_time in self.user_messages[user_id] 
            if msg_time > cutoff
        ]
        
        # Verificar si excede el límite
        return len(self.user_messages[user_id]) > self.spam_threshold
    
    async def _check_links(self, message: nextcord.Message) -> bool:
        """Verifica si hay links no permitidos"""
        content = message.content.lower()
        
        # Buscar URLs en el mensaje
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        urls = re.findall(url_pattern, content)
        
        if not urls:
            return False
        
        # Verificar si algún link no está permitido
        for url in urls:
            is_allowed = any(domain in url for domain in self.allowed_domains)
            if not is_allowed:
                return True
        
        return False
    
    async def _check_banned_words(self, message: nextcord.Message) -> bool:
        """Verifica si hay palabras prohibidas"""
        content = message.content.lower()
        
        for word in self.banned_words:
            if word in content:
                return True
        
        return False
    
    async def _check_raid(self, message: nextcord.Message) -> bool:
        """Verifica si hay actividad de raid"""
        # Verificar si el usuario es muy nuevo (menos de 1 hora)
        account_age = datetime.now(timezone.utc) - message.author.created_at
        if account_age < timedelta(hours=1):
            return True
        
        return False
    
    async def _handle_spam(self, message: nextcord.Message):
        """Maneja el spam"""
        await self._warn_user(message, "🚫 **SPAM DETECTADO**\nHas enviado demasiados mensajes muy rápido. Por favor, reduce la velocidad.")
    
    async def _handle_links(self, message: nextcord.Message):
        """Maneja links no permitidos"""
        await self._warn_user(message, "🔗 **LINK NO PERMITIDO**\nSolo se permiten links oficiales de ONZA. Otros links serán eliminados.")
    
    async def _handle_banned_words(self, message: nextcord.Message):
        """Maneja palabras prohibidas"""
        await self._warn_user(message, "⚠️ **CONTENIDO PROHIBIDO**\nEl contenido de tu mensaje no está permitido en este servidor.")
    
    async def _handle_raid(self, message: nextcord.Message):
        """Maneja actividad de raid"""
        await self._warn_user(message, "🛡️ **CUENTA NUEVA DETECTADA**\nTu cuenta es muy nueva. Por favor, espera antes de enviar mensajes.")
    
    async def _warn_user(self, message: nextcord.Message, warning_text: str):
        """Envía una advertencia al usuario"""
        try:
            # Eliminar mensaje original
            await message.delete()
            
            # Enviar advertencia privada
            try:
                embed = nextcord.Embed(
                    title="⚠️ Advertencia de Moderación",
                    description=warning_text,
                    color=0xFF6B6B,
                    timestamp=nextcord.utils.utcnow()
                )
                embed.add_field(
                    name="📋 Reglas del Servidor",
                    value="Por favor, lee las reglas del servidor para evitar futuras advertencias.",
                    inline=False
                )
                embed.set_footer(text=f"{BRAND_NAME} • Sistema de Moderación Automática")
                
                await message.author.send(embed=embed)
            except:
                # Si no puede enviar DM, enviar en el canal
                pass
            
            # Registrar en base de datos
            await self._log_moderation_action(
                user_id=message.author.id,
                action="warning",
                reason=warning_text,
                channel_id=message.channel.id
            )
            
            # Incrementar advertencias
            await self._increment_warnings(message.author.id)
            
            log.info(f"Advertencia enviada a {message.author.display_name}: {warning_text}")
            
        except Exception as e:
            log.error(f"Error enviando advertencia: {e}")
    
    async def _increment_warnings(self, user_id: int):
        """Incrementa las advertencias del usuario"""
        try:
            # Obtener advertencias actuales
            result = await db_query_one(
                "SELECT warnings FROM user_warnings WHERE user_id = ?",
                (user_id,)
            )
            
            current_warnings = result[0] if result else 0
            new_warnings = current_warnings + 1
            
            # Actualizar o insertar
            await db_execute(
                """INSERT OR REPLACE INTO user_warnings 
                   (user_id, warnings, last_warning) 
                   VALUES (?, ?, ?)""",
                (user_id, new_warnings, datetime.now(timezone.utc).timestamp())
            )
            
            # Si excede el límite, banear temporalmente
            if new_warnings >= self.max_warnings:
                await self._temp_ban_user(user_id)
            
        except Exception as e:
            log.error(f"Error incrementando advertencias: {e}")
    
    async def _temp_ban_user(self, user_id: int):
        """Banea temporalmente al usuario"""
        try:
            # Buscar el usuario en el servidor
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                return
            
            member = guild.get_member(user_id)
            if not member:
                return
            
            # Banear por 1 hora
            ban_duration = timedelta(hours=1)
            await member.timeout(ban_duration, reason="Múltiples advertencias de moderación automática")
            
            # Registrar ban
            await self._log_moderation_action(
                user_id=user_id,
                action="temp_ban",
                reason="Múltiples advertencias de moderación automática",
                channel_id=None
            )
            
            log.info(f"Usuario {member.display_name} baneado temporalmente por múltiples advertencias")
            
        except Exception as e:
            log.error(f"Error baneando usuario temporalmente: {e}")
    
    async def _log_moderation_action(self, user_id: int, action: str, reason: str, channel_id: Optional[int]):
        """Registra acciones de moderación en la base de datos"""
        try:
            await db_execute(
                """INSERT INTO moderation_logs 
                   (user_id, action, reason, channel_id, timestamp) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, action, reason, channel_id, datetime.now(timezone.utc).timestamp())
            )
        except Exception as e:
            log.error(f"Error registrando acción de moderación: {e}")

# Instancia global del moderador
auto_mod = None

def setup_auto_moderation(bot: commands.Bot):
    """Configura el sistema de moderación automática"""
    global auto_mod
    auto_mod = AutoModeration(bot)
    return auto_mod
