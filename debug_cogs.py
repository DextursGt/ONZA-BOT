#!/usr/bin/env python3
"""
Script para debuggear la carga de cogs
"""

import asyncio
import os
from dotenv import load_dotenv
from bot import ONZABot

async def debug_cogs():
    """Debuggear la carga de cogs"""
    load_dotenv()
    
    bot = ONZABot()
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ DISCORD_TOKEN no encontrado")
        return
    
    try:
        print("🔄 Iniciando bot para debug...")
        await bot.login(token)
        
        print("\n🔧 Cargando cogs...")
        bot.load_cogs()
        
        print(f"\n📊 Cogs cargados: {len(bot.cogs)}")
        for cog_name, cog in bot.cogs.items():
            print(f"  - {cog_name}: {cog}")
        
        # Esperar a que el bot esté listo
        print("\n⏳ Esperando a que el bot esté listo...")
        await asyncio.sleep(10)
        
        # Verificar estado del bot
        print(f"🤖 Bot conectado: {bot.user}")
        print(f"📊 Servidores: {len(bot.guilds)}")
        
        # Verificar servidor específico
        target_guild_id = 1408125343071736009
        guild = bot.get_guild(target_guild_id)
        if guild:
            print(f"✅ Bot está en el servidor: {guild.name} (ID: {guild.id})")
        else:
            print(f"❌ Bot NO está en el servidor ID: {target_guild_id}")
            print("🔧 Servidores donde está el bot:")
            for g in bot.guilds:
                print(f"  - {g.name} (ID: {g.id})")
        
        commands = list(bot.get_application_commands())
        print(f"\n📋 Comandos registrados: {len(commands)}")
        for cmd in commands:
            print(f"  - {cmd.name} (guild: {cmd.guild_ids})")
        
        await bot.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_cogs())
