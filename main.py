import nextcord
from nextcord.ext import commands
import asyncio
import logging
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar configuraciones
from config_new import DISCORD_TOKEN, intents, BRAND_NAME

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
            # Cargar comandos existentes
            await self.load_extension("commands.admin")
            await self.load_extension("commands.moderation") 
            await self.load_extension("commands.publication")
            await self.load_extension("commands.reviews")
            await self.load_extension("commands.user")
            
            # Cargar el nuevo sistema de tickets integrado
            await self.load_extension("commands.tickets_integrated")
            
            log.info("✅ Comandos cargados correctamente")
            
            # Inicializar base de datos
            from data_manager import load_data, save_data
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

async def main():
    """Función principal"""
    if not DISCORD_TOKEN:
        log.error("❌ DISCORD_TOKEN no encontrado en las variables de entorno")
        return
    
    bot = IntegratedONZABot()
    
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        log.error(f"❌ Error iniciando bot: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    log.info("🚀 Iniciando ONZA Bot Integrado...")
    asyncio.run(main())
