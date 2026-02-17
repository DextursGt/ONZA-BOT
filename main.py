import nextcord
from nextcord.ext import commands
import asyncio
import logging
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar configuraciones
from config import DISCORD_TOKEN, intents, BRAND_NAME

# Import dashboard bot API
from dashboard.bot_api import bot_api

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onza_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('onza-bot')

class IntegratedONZABot(commands.Bot):
    """Bot integrado que combina funcionalidades de ambos sistemas"""
    
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        self._bot_configured = False
        
    async def _setup_bot(self):
        """Configuración inicial del bot"""
        if self._bot_configured:
            return
            
        log.info("🔧 Configurando bot integrado...")
        
        try:
            # Cargar comandos directamente
            from commands.admin import AdminCommands
            from commands.moderation import ModerationCommands
            from commands.publication import PublicationCommands
            from commands.reviews import ReviewCommands
            from commands.user import UserCommands
            from commands.tickets import SimpleTicketCommands
            
            # Cargar módulo de Fortnite
            try:
                log.info("🔄 Intentando importar FortniteCommands...")
                from fortnite.fortnite_cog import FortniteCommands
                log.info("✅ FortniteCommands importado correctamente")
                
                log.info("🔄 Creando instancia de FortniteCommands...")
                fortnite_cog = FortniteCommands(self)
                log.info("✅ Instancia de FortniteCommands creada")
                
                log.info("🔄 Agregando cog al bot...")
                self.add_cog(fortnite_cog)
                log.info("✅ Cog agregado al bot")
                
                # Verificar que los comandos se registraron
                try:
                    log.info("🔄 Verificando comandos registrados...")
                    
                    # Verificar comandos del cog
                    fortnite_commands = [cmd.name for cmd in fortnite_cog.get_commands()]
                    log.info(f"📋 Comandos en el cog: {len(fortnite_commands)} comandos")
                    if fortnite_commands:
                        log.info(f"✅ Comandos Fortnite en cog: {', '.join(fortnite_commands)}")
                    else:
                        log.warning("⚠️ No se encontraron comandos en el cog de Fortnite")
                    
                    # Verificar comandos registrados en el bot
                    all_bot_commands = [cmd.name for cmd in self.commands]
                    fortnite_in_bot = [cmd for cmd in all_bot_commands if cmd.startswith('fn_')]
                    log.info(f"📋 Comandos fn_* en el bot: {len(fortnite_in_bot)} comandos")
                    if fortnite_in_bot:
                        log.info(f"✅ Comandos Fortnite en bot: {', '.join(fortnite_in_bot)}")
                    else:
                        log.error("❌ NO se encontraron comandos Fortnite registrados en el bot")
                        log.info(f"📋 Todos los comandos del bot ({len(all_bot_commands)}): {', '.join(all_bot_commands[:20])}...")
                except Exception as cmd_error:
                    log.error(f"❌ Error verificando comandos: {cmd_error}")
                    import traceback
                    log.error(f"Traceback: {traceback.format_exc()}")
            except Exception as e:
                log.error(f"❌ Error cargando módulo de Fortnite: {e}")
                import traceback
                log.error(f"Traceback completo: {traceback.format_exc()}")
            
            # Agregar cogs al bot
            self.add_cog(AdminCommands(self))
            self.add_cog(ModerationCommands(self))
            self.add_cog(PublicationCommands(self))
            self.add_cog(ReviewCommands(self))
            self.add_cog(UserCommands(self))
            self.add_cog(SimpleTicketCommands(self))
            
            # Registrar vistas persistentes
            from views.simple_ticket_view import SimpleTicketView
            from views.ticket_management_view import TicketManagementView
            self.add_view(SimpleTicketView())  # Vista simple para botones persistentes
            self.add_view(TicketManagementView())  # Vista de gestión de tickets
            
            log.info("✅ Comandos y vistas cargados correctamente")
            
            # Inicializar base de datos
            from data_manager import load_data
            data = load_data()
            log.info("✅ Base de datos inicializada")
            
            # Sincronizar comandos slash (solo si está disponible)
            try:
                if hasattr(self, 'tree'):
                    synced = await self.tree.sync()
                    log.info(f"✅ {len(synced)} comandos slash sincronizados")
                else:
                    log.info("✅ Comandos tradicionales cargados")
            except Exception as e:
                log.warning(f"⚠️ Error sincronizando comandos: {e}")
            
            # Actualizar canales e interactivos
            try:
                from events.channels import actualizar_canales_bot
                from events.interactive_messages import actualizar_mensajes_interactivos
                
                await actualizar_canales_bot(self)
                await actualizar_mensajes_interactivos(self)
                log.info("✅ Canales y mensajes interactivos actualizados")
            except Exception as e:
                log.warning(f"⚠️ Error actualizando canales/mensajes: {e}")
            
            self._bot_configured = True
            log.info("🎉 Bot integrado configurado completamente")
            
        except Exception as e:
            log.error(f"❌ Error en configuración del bot: {e}")
            raise
    
    async def on_ready(self):
        """Evento cuando el bot está listo"""
        if self._bot_configured:
            return
            
        log.info(f"🤖 {self.user} está conectado y listo!")
        log.info(f"📊 Servidores: {len(self.guilds)}")
        log.info(f"👥 Usuarios: {len(self.users)}")
        
        # Configurar actividad
        activity = nextcord.Activity(
            type=nextcord.ActivityType.playing, 
            name=f"{BRAND_NAME} - Sistema Integrado"
        )
        await self.change_presence(activity=activity)
        
        # Configurar el bot
        await self._setup_bot()
        
        log.info("🚀 Bot integrado completamente operativo!")

async def start_dashboard():
    """Iniciar servidor dashboard"""
    import uvicorn
    from dashboard.config import DASHBOARD_HOST, DASHBOARD_PORT

    config = uvicorn.Config(
        "dashboard.app:app",
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    log.info(f"🌐 Iniciando dashboard en {DASHBOARD_HOST}:{DASHBOARD_PORT}...")
    await server.serve()

async def main():
    """Función principal"""
    if not DISCORD_TOKEN:
        log.error("❌ DISCORD_TOKEN no encontrado en las variables de entorno")
        return

    bot = IntegratedONZABot()

    # Connect bot API to bot instance
    bot_api.bot = bot
    log.info("✅ Bot API conectado al dashboard")

    # Iniciar bot y dashboard en paralelo
    try:
        await asyncio.gather(
            bot.start(DISCORD_TOKEN),
            start_dashboard()
        )
    except Exception as e:
        log.error(f"❌ Error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    log.info("🚀 Iniciando ONZA Bot Integrado...")
    asyncio.run(main())
