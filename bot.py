"""
ONZA Bot - Clase principal del bot
Versión: 3.0
Autor: ONZA Team
"""

import asyncio
import logging
from datetime import datetime, timezone

import nextcord
from nextcord.ext import commands, tasks

# Importar configuración
from config import *

# Importar módulos
from utils import log, is_staff, db_execute, db_query_one, db_query_all
from i18n import t, get_user_lang
from events import BotEvents
from commands.admin import AdminCommands
from commands.user import UserCommands
from commands.tickets import TicketCommands
from commands.publication import PublicationCommands
from commands.moderation import ModerationCommands
from commands.reviews import ReviewCommands

class ONZABot(commands.Bot):
    """Clase principal del bot ONZA"""
    
    def __init__(self):
        # Configurar intents
        intents = nextcord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        # Tareas de fondo
        self.maintenance_loop = tasks.loop(minutes=30)(self.maintenance_task)
        
    async def setup_hook(self):
        """Configuración inicial del bot"""
        try:
            # Cargar extensiones
            await self.load_extension("events.bot_events")
            await self.load_extension("commands.admin")
            await self.load_extension("commands.user")
            await self.load_extension("commands.tickets")
            await self.load_extension("commands.publication")
            await self.load_extension("commands.moderation")
            await self.load_extension("commands.reviews")
            log.info("✅ Todas las extensiones cargadas correctamente")
            
            # Configurar moderación automática
            from events.moderation_events import setup_auto_moderation
            setup_auto_moderation(self)
            log.info("🛡️ Sistema de moderación automática configurado")
            
        except Exception as e:
            log.error(f"❌ Error cargando extensiones: {e}")
    
    async def on_ready(self):
        """Evento cuando el bot está listo"""
        log.info(f"🤖 Bot conectado como {self.user}")
        log.info(f"🆔 ID del bot: {self.user.id}")
        log.info(f"📊 Servidores: {len(self.guilds)}")
        
        try:
            # Inicializar base de datos del bot
            log.info("🔧 Inicializando base de datos del bot...")
            from init_db import init_bot_database
            db_result = await init_bot_database()
            if db_result:
                log.info("✅ Base de datos del bot inicializada correctamente")
            else:
                log.error("❌ Error inicializando base de datos del bot")
            
            # Inicializar base de datos de la tienda
            log.info("🔧 Inicializando base de datos de la tienda...")
            from db import ensure_store_db
            await ensure_store_db()
            log.info("✅ Bases de datos inicializadas")
            
            # Sincronizar comandos slash
            if GUILD_ID:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        log.info(f"🔄 Sincronizando comandos (intento {attempt + 1}/{max_retries})...")
                        await self.sync_all_application_commands()
                        log.info(f"✅ Comandos sincronizados correctamente en guild {GUILD_ID}")
                        
                        commands_count = len(self.application_commands)
                        log.info(f"📋 Total de comandos registrados: {commands_count}")
                        
                        command_names = [cmd.name for cmd in self.application_commands]
                        log.info(f"🔧 Comandos disponibles: {', '.join(command_names)}")
                        break
                    except Exception as e:
                        log.error(f"❌ Error sincronizando comandos (intento {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            log.info(f"⏳ Esperando {wait_time} segundos antes del siguiente intento...")
                            await asyncio.sleep(wait_time)
                        else:
                            log.error("❌ Falló la sincronización de comandos después de todos los intentos")
            
            # Inicializar canales automáticamente
            if self.guilds:
                from events import actualizar_canales_bot, actualizar_mensajes_interactivos
                await actualizar_canales_bot(self.guilds[0])
                log.info("Canales del bot inicializados automáticamente")
                
                await actualizar_mensajes_interactivos(self.guilds[0])
                log.info("Mensajes interactivos actualizados automáticamente")
            
            # Iniciar tareas de fondo
            if not self.maintenance_loop.is_running():
                self.maintenance_loop.start()
            
            log.info("🎉 Bot completamente inicializado y listo para usar")
            
        except Exception as e:
            log.error(f"Error en evento on_ready: {e}")
    
    async def maintenance_task(self):
        """Tarea de mantenimiento periódico"""
        try:
            log.info("🔧 Ejecutando tarea de mantenimiento...")
            
            # Limpiar logs antiguos
            await self.cleanup_old_logs()
            
            log.info("✅ Mantenimiento completado")
        
        except Exception as e:
            log.error(f"❌ Error en mantenimiento: {e}")
    
    async def cleanup_old_logs(self):
        """Limpiar logs antiguos de la base de datos"""
        try:
            # Eliminar logs de más de 30 días
            cutoff_date = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)
            
            await db_execute(
                "DELETE FROM interactions WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            log.info("🧹 Logs antiguos limpiados")
        
        except Exception as e:
            log.error(f"Error limpiando logs: {e}")

# Crear instancia global del bot
bot = ONZABot()
