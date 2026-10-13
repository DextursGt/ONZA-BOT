import nextcord
from nextcord.ext import commands
import asyncio
import logging
from logging.handlers import RotatingFileHandler
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
        RotatingFileHandler('onza_bot.log', maxBytes=10_000_000, backupCount=5, encoding='utf-8'),
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

        # Initialize events system databases
        from events.databases.guilds_db import GuildsDatabase
        from events.databases.invites_db import InvitesDatabase
        from events.databases.loyalty_db import LoyaltyDatabase
        self.guilds_db = GuildsDatabase()
        self.invites_db = InvitesDatabase()
        self.loyalty_db = LoyaltyDatabase()
        
    async def _setup_bot(self):
        """Configuración inicial del bot"""
        if self._bot_configured:
            return

        log.info("🔧 Configurando bot integrado...")

        try:
            # Initialize events databases
            await self.guilds_db.initialize()
            await self.invites_db.initialize()
            await self.loyalty_db.initialize()
            log.info("✅ Events databases initialized")

            # Load event handler cogs
            self.load_extension('events.cogs.join_events')
            self.load_extension('events.cogs.leave_events')
            self.load_extension('events.cogs.auto_roles')
            self.load_extension('events.cogs.invite_tracker')
            self.load_extension('events.cogs.registro_servidor')
            log.info("✅ Event handler cogs loaded")

            # Cargar comandos directamente
            from commands.admin import AdminCommands
            from commands.moderation import ModerationCommands
            from commands.publication import PublicationCommands
            from commands.reviews import ReviewCommands
            from commands.user import UserCommands
            from commands.tickets import SimpleTicketCommands

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
            
            # Subir los comandos slash a Discord. Los cogs se agregan después de conectar, así que la
            # sincronización automática de nextcord (al conectar) no los ve; `self.tree` era de discord.py
            # y nunca existió aquí, por eso solo había 2 comandos registrados.
            try:
                await self.sync_all_application_commands()
                log.info(f"✅ {len(self.get_application_commands())} comandos slash sincronizados")
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
