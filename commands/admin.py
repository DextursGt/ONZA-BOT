"""
Comandos de administración del bot ONZA
"""

import asyncio
from typing import Optional
from datetime import datetime, timezone

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion

class AdminCommands(commands.Cog):
    """Comandos de administración para staff"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="sync_commands", description="Sincronizar comandos slash (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
    async def sync_commands(self, interaction: nextcord.Interaction):
            """Forzar sincronización de comandos slash"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                await self.bot.sync_all_application_commands()
                await interaction.followup.send("✅ Comandos sincronizados correctamente.", ephemeral=True)
                
                # Log de la acción
                await log_accion("Sincronización de Comandos", interaction.user.display_name, "Comandos sincronizados manualmente")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error sincronizando comandos: {str(e)}", ephemeral=True)
                log.error(f"Error en sync_commands: {e}")
    
    @nextcord.slash_command(name="diagnostico", description="Diagnóstico del bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
    async def diagnostico(self, interaction: nextcord.Interaction):
        """Mostrar diagnóstico del bot"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Crear embed de diagnóstico
            embed = nextcord.Embed(
                title="🔧 Diagnóstico del Bot",
                color=nextcord.Color.blue(),
                timestamp=nextcord.utils.utcnow()
            )
            
            # Información del bot
            embed.add_field(
                name="🤖 **Bot**",
                value=f"• **Nombre:** {self.bot.user.name}\n• **ID:** {self.bot.user.id}\n• **Servidores:** {len(self.bot.guilds)}",
                inline=False
            )
            
            # Información del servidor
            if interaction.guild:
                embed.add_field(
                    name="🏠 **Servidor**",
                    value=f"• **Nombre:** {interaction.guild.name}\n• **ID:** {interaction.guild.id}\n• **Miembros:** {interaction.guild.member_count}",
                    inline=False
                )
            
            # Comandos registrados
            commands_count = len(list(self.bot.get_application_commands()))
            embed.add_field(
                name="⚙️ **Comandos**",
                value=f"• **Total:** {commands_count}\n• **Estado:** {'✅ Activos' if commands_count > 0 else '❌ Sin comandos'}",
                inline=False
            )
            
            # Estado de conexión
            embed.add_field(
                name="🌐 **Conexión**",
                value=f"• **Estado:** {'✅ Conectado' if self.bot.is_ready() else '❌ Desconectado'}\n• **Latencia:** {round(self.bot.latency * 1000)}ms",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Diagnóstico")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            await log_accion("Diagnóstico", interaction.user.display_name, "Diagnóstico ejecutado")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error en diagnóstico: {str(e)}", ephemeral=True)
            log.error(f"Error en diagnostico: {e}")
    
    @nextcord.slash_command(name="reiniciar_bot", description="Reiniciar el bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
    async def reiniciar_bot(self, interaction: nextcord.Interaction):
        """Reiniciar el bot (solo para administradores)"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            await interaction.response.send_message("🔄 Reiniciando bot...", ephemeral=True)
            
            # Log de la acción
            await log_accion("Reinicio del Bot", interaction.user.display_name, "Bot reiniciado por comando")
            
            # Cerrar el bot
            await self.bot.close()
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error reiniciando bot: {str(e)}", ephemeral=True)
            log.error(f"Error en reiniciar_bot: {e}")