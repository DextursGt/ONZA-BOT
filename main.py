"""
ONZA Bot - Punto de entrada principal
Versión: 3.0
Autor: ONZA Team
"""

import asyncio
import sys
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar el bot
from bot import ONZABot

def setup_logging():
    """Configurar el sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('onza_bot.log', encoding='utf-8')
        ]
    )

async def main():
    """Función principal del bot"""
    try:
        # Configurar logging
        setup_logging()
        
        # Crear instancia del bot
        bot = ONZABot()
        
        # Keep-alive no necesario en VPS dedicado
        
        # Iniciar el bot
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"💥 Error crítico: {e}")
        sys.exit(1)
