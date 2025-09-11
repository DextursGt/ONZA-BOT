"""
Sistema de moderación automática avanzado para ONZA Bot
Versión: 3.1 - MEJORADO
"""

import re
import logging
import hashlib
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set
from collections import defaultdict, deque

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, db_execute, db_query_one, db_query_all

class AutoModeration:
    """Sistema de moderación automática"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Sistema de tracking mejorado
        self.user_messages = defaultdict(lambda: deque(maxlen=50))  # Últimos 50 mensajes por usuario
        self.user_warnings = defaultdict(int)  # Contador de advertencias por usuario
        self.user_join_times = {}  # Tiempo de unión al servidor
        self.duplicate_messages = defaultdict(list)  # Detección de mensajes duplicados
        self.suspicious_users = set()  # Usuarios marcados como sospechosos
        self.rate_limits = defaultdict(lambda: {'count': 0, 'reset_time': 0})  # Rate limiting por usuario
        
        # Configuración de moderación MEJORADA
        self.max_warnings = 3
        self.warning_cooldown = 300  # 5 minutos
        self.spam_threshold = 4  # 4 mensajes (más estricto)
        self.spam_timeframe = 8  # en 8 segundos (más estricto)
        self.duplicate_threshold = 3  # 3 mensajes duplicados
        self.duplicate_timeframe = 60  # en 60 segundos
        self.raid_detection_threshold = 5  # 5 usuarios nuevos en 5 minutos
        self.raid_timeframe = 300  # 5 minutos
        
        # Links permitidos (solo de ONZA) - MEJORADO
        self.allowed_domains = [
            'onza.com', 'onza.mx', 'onza.net', 'onza.org',
            'discord.gg/onza', 'discord.com/invite/onza',
            't.me/onza', 'telegram.me/onza',
            'github.com/onza', 'gitlab.com/onza'
        ]
        
        # Palabras prohibidas MEJORADAS (spam/raid/scam)
        self.banned_words = [
            # Links externos
            'discord.gg/', 'discord.com/invite/', 'discordapp.com/invite/',
            't.me/', 'telegram.me/', 'youtube.com/watch', 'youtu.be/',
            'bit.ly/', 'tinyurl.com/', 'short.link/', 'cutt.ly/',
            'steamcommunity.com', 'steamdb.info', 'steamrep.com',
            'twitch.tv/', 'instagram.com/', 'facebook.com/', 'twitter.com/',
            'reddit.com/', 'tiktok.com/', 'snapchat.com/',
            
            # Scams y spam
            'free nitro', 'nitro gratis', 'discord nitro free',
            'steam gift', 'steam wallet', 'steam key',
            'free robux', 'robux generator', 'roblox free',
            'minecraft premium', 'minecraft free',
            'spotify premium free', 'netflix free',
            'hack', 'crack', 'generator', 'free money',
            'click here', 'join now', 'limited time',
            'dm me', 'pm me', 'add me', 'follow me',
            
            # Contenido inapropiado
            'nsfw', 'porn', 'sex', 'fuck', 'shit', 'bitch',
            'kill yourself', 'kys', 'suicide', 'self harm',
            'drugs', 'weed', 'cocaine', 'marijuana',
            
            # Raid y spam
            '@everyone', '@here', 'raid', 'spam',
            'bot', 'automated', 'script', 'macro'
        ]
        
        # Patrones de detección avanzada
        self.url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'discord\.gg/[a-zA-Z0-9]+',
            r't\.me/[a-zA-Z0-9_]+'
        ]
        
        # Sistema de cooldowns por tipo de infracción
        self.cooldowns = {
            'spam': 30,      # 30 segundos
            'links': 60,     # 1 minuto
            'banned_words': 120,  # 2 minutos
            'raid': 300,     # 5 minutos
            'duplicate': 60  # 1 minuto
        }
    
    async def check_message(self, message: nextcord.Message) -> bool:
        """
        Verifica un mensaje y aplica moderación automática MEJORADA
        Retorna True si el mensaje debe ser eliminado
        """
        try:
            # Ignorar staff y bots
            if is_staff(message.author) or message.author.bot:
                return False
            
            user_id = message.author.id
            now = datetime.now(timezone.utc)
            
            # Verificar rate limiting
            if await self._check_rate_limit(user_id, 'general'):
                return True
            
            # 1. Verificar spam (más estricto)
            if await self._check_spam_advanced(message):
                await self._handle_spam(message)
                await self._apply_cooldown(user_id, 'spam')
                return True
            
            # 2. Verificar mensajes duplicados
            if await self._check_duplicate_messages(message):
                await self._handle_duplicate_messages(message)
                await self._apply_cooldown(user_id, 'duplicate')
                return True
            
            # 3. Verificar links no permitidos (mejorado)
            if await self._check_links_advanced(message):
                await self._handle_links(message)
                await self._apply_cooldown(user_id, 'links')
                return True
            
            # 4. Verificar palabras prohibidas (mejorado)
            if await self._check_banned_words_advanced(message):
                await self._handle_banned_words(message)
                await self._apply_cooldown(user_id, 'banned_words')
                return True
            
            # 5. Verificar raids (mejorado)
            if await self._check_raid_advanced(message):
                await self._handle_raid(message)
                await self._apply_cooldown(user_id, 'raid')
                return True
            
            # 6. Verificar contenido sospechoso
            if await self._check_suspicious_content(message):
                await self._handle_suspicious_content(message)
                return True
            
            # 7. Verificar menciones excesivas
            if await self._check_excessive_mentions(message):
                await self._handle_excessive_mentions(message)
                return True
            
            # Si llegamos aquí, el mensaje es válido
            # Actualizar tracking del usuario
            self.user_messages[user_id].append({
                'timestamp': now,
                'content': message.content,
                'channel_id': message.channel.id
            })
            
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
