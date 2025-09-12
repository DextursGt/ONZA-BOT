#!/usr/bin/env python3
"""
Script para diagnosticar comandos del bot
"""

import asyncio
import os
from dotenv import load_dotenv
from bot import ONZABot

async def diagnose_commands():
    """Diagnosticar comandos del bot"""
    load_dotenv()
    
    bot = ONZABot()
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ DISCORD_TOKEN no encontrado")
        return
    
    try:
        print("🔄 Iniciando bot para diagnóstico...")
        await bot.login(token)
        
        # Cargar cogs
        bot.load_cogs()
        
        # Esperar a que el bot esté listo
        print("⏳ Esperando a que el bot esté listo...")
        await asyncio.sleep(5)
        
        # Verificar estado del bot
        print(f"🤖 Bot conectado: {bot.user}")
        print(f"📊 Servidores: {len(bot.guilds)}")
        
        # Obtener comandos
        commands = list(bot.get_application_commands())
        print(f"\n📊 Total de comandos: {len(commands)}")
        
        print("\n🔧 Comandos disponibles:")
        for i, cmd in enumerate(commands, 1):
            print(f"  {i:2d}. {cmd.name} (guild: {cmd.guild_ids})")
        
        # Verificar comandos específicos
        command_names = [cmd.name for cmd in commands]
        expected_commands = [
            'help', 'panel', 'sync_commands', 'diagnostico', 'cerrar_mi_ticket',
            'servicios', 'pagos', 'publicar_bot', 'banear', 'limpiar',
            'reseña', 'reseña_aprobar', 'limpiar_tickets', 'reiniciar_bot'
        ]
        
        print(f"\n✅ Comandos esperados: {len(expected_commands)}")
        print(f"📋 Comandos encontrados: {len(commands)}")
        
        missing_commands = [cmd for cmd in expected_commands if cmd not in command_names]
        if missing_commands:
            print(f"\n❌ Comandos faltantes: {', '.join(missing_commands)}")
        else:
            print("\n✅ Todos los comandos están presentes")
        
        await bot.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_commands())
