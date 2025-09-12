#!/usr/bin/env python3
"""
Script para forzar sincronización de comandos
"""

import asyncio
import os
from dotenv import load_dotenv
from bot import ONZABot

async def force_sync():
    """Forzar sincronización de comandos"""
    load_dotenv()
    
    bot = ONZABot()
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ DISCORD_TOKEN no encontrado")
        return
    
    try:
        print("🔄 Iniciando bot para sincronización...")
        await bot.login(token)
        
        print("🔄 Sincronizando comandos...")
        synced = await bot.sync_all_application_commands()
        print(f"✅ Comandos sincronizados: {synced}")
        
        # Esperar un poco
        await asyncio.sleep(3)
        
        # Verificar comandos
        commands = list(bot.get_application_commands())
        print(f"📊 Comandos verificados: {len(commands)}")
        for cmd in commands:
            print(f"  - {cmd.name}")
        
        await bot.close()
        print("✅ Sincronización completada")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(force_sync())
