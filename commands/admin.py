"""
Comandos de administración del bot ONZA
"""

import asyncio
from typing import Optional

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion

class AdminCommands:
    """Comandos de administración para staff"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._register_commands()
    
    def _register_commands(self):
        """Registrar comandos de administración"""
        
        @self.bot.slash_command(name="sync_commands", description="Sincronizar comandos slash (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def sync_commands(interaction: nextcord.Interaction):
            """Forzar sincronización de comandos slash"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                await self.bot.sync_all_application_commands()
                
                # Mostrar información de comandos
                commands_count = len(self.bot.application_commands)
                commands_list = [f"• `/{cmd.name}`" for cmd in self.bot.application_commands[:10]]
                commands_text = "\n".join(commands_list)
                if commands_count > 10:
                    commands_text += f"\n... y {commands_count - 10} más"
                
                success_embed = nextcord.Embed(
                    title="✅ **Comandos Sincronizados**",
                    description=f"Sincronizados **{commands_count}** comandos correctamente.",
                    color=0x00FF00,
                    timestamp=nextcord.utils.utcnow()
                )
                
                success_embed.add_field(
                    name="📋 **Comandos registrados**",
                    value=commands_text,
                    inline=False
                )
                
                success_embed.add_field(
                    name="⏰ **Tiempo de aparición**",
                    value="• **5-15 minutos**: Tiempo normal\n• **Hasta 1 hora**: En casos excepcionales",
                    inline=False
                )
                
                success_embed.add_field(
                    name="🔧 **Si no aparecen**",
                    value="1. Espera unos minutos\n2. Reinicia Discord\n3. Verifica permisos del bot\n4. Usa este comando nuevamente",
                    inline=False
                )
                
                success_embed.set_footer(text="ONZA Bot • Sistema de Sincronización")
                
                await interaction.followup.send(embed=success_embed, ephemeral=True)
                log.info(f"Comandos sincronizados manualmente por {interaction.user.display_name}")
                
            except Exception as e:
                error_embed = nextcord.Embed(
                    title="❌ **Error de Sincronización**",
                    description=f"Error al sincronizar comandos: {str(e)}",
                    color=0xFF0000,
                    timestamp=nextcord.utils.utcnow()
                )
                
                error_embed.add_field(
                    name="🔧 **Soluciones**",
                    value="1. Verifica que el bot tenga permisos de administrador\n2. Intenta nuevamente en unos minutos\n3. Contacta al desarrollador si persiste",
                    inline=False
                )
                
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                log.error(f"Error en sincronización manual: {e}")
        
        @self.bot.slash_command(name="diagnostico", description="Diagnosticar estado del bot y comandos (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def diagnostico(interaction: nextcord.Interaction):
            """Diagnosticar el estado del bot y sus comandos"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Información del bot
                bot_info = f"**Bot:** {self.bot.user.name}#{self.bot.user.discriminator}\n**ID:** {self.bot.user.id}\n**Servidores:** {len(self.bot.guilds)}"
                
                # Información de comandos
                commands_count = len(self.bot.application_commands)
                commands_list = [f"• `/{cmd.name}`" for cmd in self.bot.application_commands]
                commands_text = "\n".join(commands_list) if commands_list else "❌ No hay comandos registrados"
                
                # Verificar comandos específicos
                specific_commands = ["publicar_metodos_pago", "banear", "reiniciar_render", "sync_commands", "diagnostico"]
                command_status = []
                
                for cmd_name in specific_commands:
                    if any(cmd.name == cmd_name for cmd in self.bot.application_commands):
                        command_status.append(f"✅ `/{cmd_name}` - Registrado")
                    else:
                        command_status.append(f"❌ `/{cmd_name}` - No encontrado")
                
                # Información del servidor
                guild_info = f"**Servidor:** {interaction.guild.name}\n**ID:** {interaction.guild.id}\n**Miembros:** {interaction.guild.member_count}"
                
                # Permisos del bot
                bot_permissions = []
                if interaction.guild.me.guild_permissions.administrator:
                    bot_permissions.append("✅ Administrador")
                else:
                    bot_permissions.append("❌ No es administrador")
                
                if interaction.guild.me.guild_permissions.manage_channels:
                    bot_permissions.append("✅ Gestionar canales")
                else:
                    bot_permissions.append("❌ No puede gestionar canales")
                
                if interaction.guild.me.guild_permissions.ban_members:
                    bot_permissions.append("✅ Banear miembros")
                else:
                    bot_permissions.append("❌ No puede banear miembros")
                
                # Crear embed de diagnóstico
                embed = nextcord.Embed(
                    title="🔍 **Diagnóstico del Bot**",
                    description="Información completa del estado del bot",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="🤖 **Información del Bot**",
                    value=bot_info,
                    inline=False
                )
                
                embed.add_field(
                    name="🏠 **Información del Servidor**",
                    value=guild_info,
                    inline=False
                )
                
                embed.add_field(
                    name="📋 **Comandos Registrados**",
                    value=f"**Total:** {commands_count}\n{commands_text[:1000]}{'...' if len(commands_text) > 1000 else ''}",
                    inline=False
                )
                
                embed.add_field(
                    name="🔍 **Estado de Comandos Específicos**",
                    value="\n".join(command_status),
                    inline=False
                )
                
                embed.add_field(
                    name="🔐 **Permisos del Bot**",
                    value="\n".join(bot_permissions),
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Sistema de Diagnóstico")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Diagnóstico Ejecutado", interaction.user.display_name, f"Comandos: {commands_count}")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error en diagnóstico: {str(e)}", ephemeral=True)
                log.error(f"Error en diagnostico: {e}")
        
        @self.bot.slash_command(name="reiniciar_render", description="Reiniciar el servicio de Render (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def reiniciar_render(interaction: nextcord.Interaction):
            """Reiniciar el servicio de Render desde Discord"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Mostrar embed informativo
                info_embed = nextcord.Embed(
                    title="🔄 **Reiniciar Servicio Render**",
                    description="Para reiniciar el servicio de Render, sigue estos pasos:",
                    color=0xFFA500,
                    timestamp=nextcord.utils.utcnow()
                )
                
                info_embed.add_field(
                    name="📋 **Pasos para reiniciar:**",
                    value="1. Ve a [Render Dashboard](https://dashboard.render.com)\n2. Busca el servicio 'onza-bot'\n3. Haz clic en 'Manual Deploy'\n4. Selecciona 'Deploy latest commit'\n5. Espera a que termine el despliegue",
                    inline=False
                )
                
                info_embed.add_field(
                    name="⏰ **Tiempo estimado:**",
                    value="• **2-5 minutos** para el reinicio completo\n• El bot estará offline durante el proceso",
                    inline=False
                )
                
                info_embed.add_field(
                    name="🔍 **Verificar estado:**",
                    value="• Revisa los logs en Render Dashboard\n• Usa `/diagnostico` después del reinicio\n• Verifica que los comandos funcionen",
                    inline=False
                )
                
                info_embed.set_footer(text="ONZA Bot • Sistema de Reinicio")
                
                await interaction.followup.send(embed=info_embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Reinicio Render Solicitado", interaction.user.display_name, "Instrucciones proporcionadas")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error mostrando información: {str(e)}", ephemeral=True)
                log.error(f"Error en reiniciar_render: {e}")
