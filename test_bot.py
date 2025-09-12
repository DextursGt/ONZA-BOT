#!/usr/bin/env python3
"""
Bot de prueba simple para diagnosticar problemas de comandos
"""

import asyncio
import os
from dotenv import load_dotenv
import nextcord
from nextcord.ext import commands

# Cargar variables de entorno
load_dotenv()

# Configuración
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))

class TestBot(commands.Bot):
    def __init__(self):
        intents = nextcord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
    
    async def on_ready(self):
        print(f"🤖 Bot conectado como {self.user}")
        print(f"🆔 ID: {self.user.id}")
        print(f"📊 Servidores: {len(self.guilds)}")
        
        if GUILD_ID:
            guild = self.get_guild(GUILD_ID)
            if guild:
                print(f"🏠 Guild encontrado: {guild.name} (ID: {guild.id})")
            else:
                print(f"❌ Guild {GUILD_ID} no encontrado")
        
        # Sincronizar comandos
        try:
            print("🔄 Sincronizando comandos...")
            synced = await self.sync_all_application_commands()
            print(f"✅ Comandos sincronizados: {synced}")
            
            # Verificar comandos
            commands = list(self.get_application_commands())
            print(f"📋 Comandos registrados: {len(commands)}")
            for cmd in commands:
                print(f"  - {cmd.name}")
                
        except Exception as e:
            print(f"❌ Error sincronizando: {e}")

# Comando de prueba
@nextcord.slash_command(name="test", description="Comando de prueba", guild_ids=[GUILD_ID] if GUILD_ID else None)
async def test_command(interaction: nextcord.Interaction):
    await interaction.response.send_message("✅ Comando de prueba funcionando!")

async def main():
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN no configurado")
        return
    
    if not GUILD_ID:
        print("❌ GUILD_ID no configurado")
        return
    
    bot = TestBot()
    bot.add_application_command(test_command)
    
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error iniciando bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
