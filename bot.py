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
        
        # Los cogs se cargarán en on_ready para evitar conflictos
        self._bot_configured = False
        
    def load_cogs(self):
        """Cargar todos los cogs del bot"""
        try:
            self.add_cog(AdminCommands(self))
            self.add_cog(UserCommands(self))
            self.add_cog(TicketCommands(self))
            self.add_cog(PublicationCommands(self))
            self.add_cog(ModerationCommands(self))
            self.add_cog(ReviewCommands(self))
            log.info("✅ Todos los cogs cargados correctamente")
        except Exception as e:
            log.error(f"❌ Error cargando cogs: {e}")
        
    async def _setup_bot(self):
        """Configuración inicial del bot (llamado desde on_ready)"""
        log.info("🚀 Iniciando configuración del bot...")
        try:
            # Cargar eventos (comentado temporalmente para evitar conflictos)
            # log.info("📦 Cargando extensión de eventos...")
            # await self.load_extension("events.bot_events")
            # log.info("✅ Eventos cargados correctamente")
            
            # Instanciar y registrar eventos
            log.info("🔧 Instanciando eventos del bot...")
            self.bot_events = BotEvents(self)
            self.add_listener(self.bot_events.on_member_join, "on_member_join")
            self.add_listener(self.bot_events.on_message, "on_message")
            self.add_listener(self.bot_events.on_guild_join, "on_guild_join")
            self.add_listener(self.bot_events.on_interaction, "on_interaction")
            log.info("✅ Eventos registrados correctamente")
            
            # Configurar moderación automática
            log.info("🛡️ Configurando moderación automática...")
            from events.moderation_events import setup_auto_moderation
            setup_auto_moderation(self)
            log.info("✅ Sistema de moderación automática configurado")
            
            # Los comandos ya se cargan en load_cogs() antes de este método
            log.info("✅ Comandos ya cargados en load_cogs()")
            log.info("🎉 Configuración del bot completada exitosamente")
            return True
            
        except Exception as e:
            log.error(f"❌ Error en configuración del bot: {e}")
            import traceback
            log.error(f"💥 Traceback completo: {traceback.format_exc()}")
            return False
    
    async def on_ready(self):
        """Evento cuando el bot está listo"""
        print("🚀🚀🚀 EVENTO ON_READY EJECUTÁNDOSE 🚀🚀🚀")
        log.info("🚀🚀🚀 EVENTO ON_READY EJECUTÁNDOSE 🚀🚀🚀")
        log.info(f"🤖 Bot conectado como {self.user}")
        log.info(f"🆔 ID del bot: {self.user.id}")
        log.info(f"📊 Servidores: {len(self.guilds)}")
        
        # Variable para evitar ejecutar la configuración múltiples veces
        if self._bot_configured:
            log.info("⚠️ Bot ya configurado, saltando configuración")
            return
            
        try:
            # Cargar cogs primero
            log.info("🔧 Cargando cogs...")
            self.load_cogs()
            
            # Configurar el bot (eventos, etc.)
            setup_success = await self._setup_bot()
            if not setup_success:
                log.error("❌ Error en la configuración del bot")
                return
            
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
                        
                        # Limpiar comandos existentes primero
                        try:
                            await self.sync_all_application_commands(force=True)
                        except Exception as sync_error:
                            log.warning(f"⚠️ Error en sync inicial: {sync_error}")
                        
                        # Esperar un poco para que Discord procese
                        await asyncio.sleep(2)
                        
                        # Verificar comandos registrados
                        commands_count = len(self.get_application_commands())
                        log.info(f"📋 Total de comandos registrados: {commands_count}")
                        
                        if commands_count > 0:
                            command_names = [cmd.name for cmd in self.get_application_commands()]
                            log.info(f"🔧 Comandos disponibles: {', '.join(command_names)}")
                            log.info(f"✅ Comandos sincronizados correctamente en guild {GUILD_ID}")
                            break
                        else:
                            log.warning(f"⚠️ No se registraron comandos en intento {attempt + 1}")
                            
                    except Exception as e:
                        log.error(f"❌ Error sincronizando comandos (intento {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5
                            log.info(f"⏳ Esperando {wait_time} segundos antes del siguiente intento...")
                            await asyncio.sleep(wait_time)
                else:
                    log.error("❌ Falló la sincronización de comandos después de todos los intentos")
            else:
                log.error("❌ GUILD_ID no configurado, no se pueden sincronizar comandos")
            
            # Inicializar canales automáticamente
            if self.guilds:
                try:
                    from events.channels import actualizar_canales_bot
                    from events.interactive_messages import actualizar_mensajes_interactivos
                    await actualizar_canales_bot(self.guilds[0])
                    log.info("Canales del bot inicializados automáticamente")
                    
                    await actualizar_mensajes_interactivos(self.guilds[0])
                    log.info("Mensajes interactivos actualizados automáticamente")
                except Exception as e:
                    log.error(f"Error inicializando canales: {e}")
            
            # Iniciar tareas de fondo
            if self.maintenance_loop is None:
                self.maintenance_loop = tasks.loop(minutes=30)(self.maintenance_task)
                self.maintenance_loop.start()
            elif not self.maintenance_loop.is_running():
                self.maintenance_loop.start()
            
            # Marcar como configurado
            self._bot_configured = True
            log.info("🎉 Bot completamente inicializado y listo para usar")
            
        except Exception as e:
            log.error(f"Error en evento on_ready: {e}")
            import traceback
            log.error(f"Traceback completo: {traceback.format_exc()}")
    
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
    

# La instancia del bot se crea en main.py
