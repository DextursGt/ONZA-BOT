"""
Comandos de administración del bot ONZA
"""

import asyncio

import nextcord
from utils import PERMISO_STAFF
from nextcord.ext import commands

from config import *
import os
from utils import log, is_staff, is_admin, log_accion

class AdminCommands(commands.Cog):
    """Comandos de administración para staff"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="sync_commands", default_member_permissions=PERMISO_STAFF, description="Sincronizar comandos slash (solo admin)", guild_ids=[1408125343071736009])
    async def sync_commands(self, interaction: nextcord.Interaction):
        """Forzar sincronización de comandos slash"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Contar comandos antes
            try:
                commands_before = len(list(self.bot.get_application_commands()))
            except Exception:
                commands_before = 0
            
            await self.bot.subir_comandos()
            sync_success = True

            # Esperar un poco
            await asyncio.sleep(2)
            
            # Contar comandos después
            try:
                commands_after = len(list(self.bot.get_application_commands()))
                command_names = [cmd.name for cmd in self.bot.get_application_commands()]
            except Exception:
                commands_after = 0
                command_names = []
            
            embed = nextcord.Embed(
                title="🔄 Sincronización de Comandos",
                color=nextcord.Color.green(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📊 **Resultado**",
                value=f"• **Antes:** {commands_before} comandos\n• **Después:** {commands_after} comandos\n• **Sincronización:** {'✅ Exitosa' if sync_success else '❌ Fallida'}\n• **Estado:** {'✅ Exitoso' if commands_after > 0 else '❌ Fallido'}",
                inline=False
            )
            
            if command_names:
                embed.add_field(
                    name="🔧 **Comandos Disponibles**",
                    value=f"`{', '.join(command_names)}`",
                    inline=False
                )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Sincronización")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            log_accion("Sincronización de Comandos", interaction.user.display_name, f"Antes: {commands_before}, Después: {commands_after}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error sincronizando comandos: {str(e)}", ephemeral=True)
            log.error(f"Error en sync_commands: {e}")
    
    @nextcord.slash_command(name="diagnostico", default_member_permissions=PERMISO_STAFF, description="Diagnóstico del bot (solo admin)", guild_ids=[1408125343071736009])
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
            try:
                commands_count = len(list(self.bot.get_application_commands()))
                command_names = [cmd.name for cmd in self.bot.get_application_commands()]
            except Exception:
                commands_count = 0
                command_names = []
            
            embed.add_field(
                name="⚙️ **Comandos**",
                value=f"• **Total:** {commands_count}\n• **Estado:** {'✅ Activos' if commands_count > 0 else '❌ Sin comandos'}\n• **Lista:** {', '.join(command_names) if command_names else 'Ninguno'}",
                inline=False
            )
            
            # Estado de conexión
            embed.add_field(
                name="🌐 **Conexión**",
                value=f"• **Estado:** {'✅ Conectado' if self.bot.is_ready() else '❌ Desconectado'}\n• **Latencia:** {round(self.bot.latency * 1000)}ms",
                inline=False
            )
            
            # Estado de configuración
            embed.add_field(
                name="🔧 **Configuración**",
                value=f"• **Bot configurado:** {'✅ Sí' if hasattr(self.bot, '_bot_configured') and self.bot._bot_configured else '❌ No'}\n• **Cogs cargados:** {len(self.bot.cogs)}",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Diagnóstico")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            log_accion("Diagnóstico", interaction.user.display_name, f"Comandos: {commands_count}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error en diagnóstico: {str(e)}", ephemeral=True)
            log.error(f"Error en diagnostico: {e}")
    
    @nextcord.slash_command(name="reiniciar_bot", default_member_permissions=PERMISO_STAFF, description="Reiniciar el bot (solo admin)")
    async def reiniciar_bot(self, interaction: nextcord.Interaction):
        """Reiniciar el bot (solo para administradores)"""
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Solo owner/staff pueden usar este comando.", ephemeral=True)
            return
        
        try:
            await interaction.response.send_message("🔄 Reiniciando bot...", ephemeral=True)
            
            # Log de la acción
            log_accion("Reinicio del Bot", interaction.user.display_name, "Bot reiniciado por comando")
            
            # Salir del proceso para que PM2 lo levante (bot.close() dejaba vivo al dashboard y nadie reiniciaba)
            await self.bot.close()
            os._exit(1)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error reiniciando bot: {str(e)}", ephemeral=True)
            log.error(f"Error en reiniciar_bot: {e}")

    @commands.command(name="admin", description="Comandos de administración")
    async def admin_command(self, ctx):
        """Comando tradicional de administración"""
        if not is_staff(ctx.author):
            await ctx.send("❌ Solo el staff puede usar este comando.")
            return
        
        embed = nextcord.Embed(
            title="👑 Comandos de Administración",
            description="Comandos disponibles para administradores:",
            color=0xFF0000,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="🔧 **Comandos Disponibles**",
            value="• `/sync_commands` - Sincronizar comandos slash\n• `/diagnostico` - Diagnóstico del bot\n• `/reiniciar_bot` - Reiniciar el bot",
            inline=False
        )
        
        embed.add_field(
            name="📊 **Información del Bot**",
            value=f"• **Servidores:** {len(self.bot.guilds)}\n• **Usuarios:** {len(self.bot.users)}\n• **Latencia:** {round(self.bot.latency * 1000)}ms",
            inline=False
        )
        
        embed.set_footer(text=f"{BRAND_NAME} • Comandos de Admin")
        
        await ctx.send(embed=embed)

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(AdminCommands(bot))