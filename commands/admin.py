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
                specific_commands = ["publicar_metodos_pago", "banear", "reiniciar_bot", "sync_commands", "diagnostico"]
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
        
        @self.bot.slash_command(name="reiniciar_bot", description="Reiniciar el bot (solo admin con contraseña)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def reiniciar_bot(interaction: nextcord.Interaction, password: str):
            """Reiniciar el bot desde Discord con contraseña"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Verificar contraseña
                if password != "OnzaTestur":
                    error_embed = nextcord.Embed(
                        title="❌ **Contraseña Incorrecta**",
                        description="La contraseña proporcionada no es válida.",
                        color=0xFF0000,
                        timestamp=nextcord.utils.utcnow()
                    )
                    error_embed.add_field(
                        name="🔒 **Seguridad:**",
                        value="Este comando requiere la contraseña correcta para reiniciar el bot.",
                        inline=False
                    )
                    error_embed.set_footer(text="ONZA Bot • Sistema de Seguridad")
                    
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                    
                    # Log de intento fallido
                    await log_accion("Intento de Reinicio Fallido", interaction.user.display_name, f"Contraseña incorrecta: {password[:3]}***")
                    return
                
                # Contraseña correcta - proceder con el reinicio
                success_embed = nextcord.Embed(
                    title="🔄 **Reiniciando Bot**",
                    description="✅ Contraseña verificada correctamente.\n\n**El bot se reiniciará en 5 segundos...**",
                    color=0x00FF00,
                    timestamp=nextcord.utils.utcnow()
                )
                
                success_embed.add_field(
                    name="⏰ **Proceso de Reinicio:**",
                    value="1. ✅ Contraseña verificada\n2. 🔄 Reiniciando servicios...\n3. 📡 Reconectando a Discord\n4. 🎯 Sincronizando comandos\n5. ✅ Bot listo",
                    inline=False
                )
                
                success_embed.add_field(
                    name="🔍 **Verificar después del reinicio:**",
                    value="• Usa `/diagnostico` para verificar estado\n• Prueba `/help` para confirmar comandos\n• Revisa logs si hay problemas",
                    inline=False
                )
                
                success_embed.set_footer(text="ONZA Bot • Reinicio Autorizado")
                
                await interaction.followup.send(embed=success_embed, ephemeral=True)
                
                # Log de la acción exitosa
                await log_accion("Reinicio Bot Autorizado", interaction.user.display_name, "Contraseña verificada correctamente")
                
                # Esperar 5 segundos y luego reiniciar
                await asyncio.sleep(5)
                
                # Cerrar el bot (esto causará que Supervisor lo reinicie)
                log.info(f"🔄 Bot reiniciado por {interaction.user.display_name}")
                await self.bot.close()
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error durante el reinicio: {str(e)}", ephemeral=True)
                log.error(f"Error en reiniciar_bot: {e}")
      
        @self.bot.slash_command(name="configurar_canal", description="Configurar canales del bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def configurar_canal(interaction: nextcord.Interaction):
            """Configurar canales del bot"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Mostrar canales actuales
                embed = nextcord.Embed(
                    title="⚙️ **Configuración de Canales**",
                    description="Canales configurados actualmente:",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                from config import CANALES_BOT
                for canal_tipo, canal_id in CANALES_BOT.items():
                    canal = interaction.guild.get_channel(canal_id)
                    embed.add_field(
                        name=f"📋 **{canal_tipo.title()}**",
                        value=f"{canal.mention if canal else 'No configurado'}",
                        inline=True
                    )
                
                embed.add_field(
                    name="ℹ️ **Información**",
                    value="Los canales se configuran automáticamente al iniciar el bot.",
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Configuración de Canales")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Configuración de Canales Consultada", interaction.user.display_name)
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error mostrando configuración: {str(e)}", ephemeral=True)
                log.error(f"Error en configurar_canal: {e}")
        
        @self.bot.slash_command(name="limpiar", description="Limpiar mensajes del canal (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def limpiar(interaction: nextcord.Interaction, cantidad: int = nextcord.SlashOption(description="Cantidad de mensajes a eliminar", min_value=1, max_value=100)):
            """Limpiar mensajes del canal"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Verificar permisos
                if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                    await interaction.followup.send("❌ No tengo permisos para eliminar mensajes en este canal.", ephemeral=True)
                    return
                
                # Eliminar mensajes
                deleted = 0
                async for message in interaction.channel.history(limit=cantidad):
                    try:
                        await message.delete()
                        deleted += 1
                    except:
                        pass
                
                embed = nextcord.Embed(
                    title="🧹 **Limpieza Completada**",
                    description=f"Se eliminaron **{deleted}** mensajes del canal.",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 **Resumen**",
                    value=f"• **Solicitados:** {cantidad}\n• **Eliminados:** {deleted}",
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Sistema de Limpieza")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Limpieza de Canal", interaction.user.display_name, f"Canal: {interaction.channel.name}, Eliminados: {deleted}")
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error limpiando canal: {str(e)}", ephemeral=True)
                log.error(f"Error en limpiar: {e}")
        
        @self.bot.slash_command(name="actualizar_canales", description="Actualizar lista de canales del bot (solo admin)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def actualizar_canales(interaction: nextcord.Interaction):
            """Actualizar canales del bot"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
                
                # Actualizar canales
                from events.channels import actualizar_canales_bot
                await actualizar_canales_bot(interaction.guild)
                
                embed = nextcord.Embed(
                    title="✅ **Canales Actualizados**",
                    description="La lista de canales del bot ha sido actualizada correctamente.",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📋 **Canales Encontrados**",
                    value="Los canales se han detectado automáticamente por nombre.",
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Sistema de Canales")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Canales Actualizados", interaction.user.display_name)
                
            except Exception as e:
                await interaction.followup.send(f"❌ Error actualizando canales: {str(e)}", ephemeral=True)
                log.error(f"Error en actualizar_canales: {e}")
        
        @self.bot.slash_command(name="canal_id", description="Obtener ID de un canal", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def canal_id(interaction: nextcord.Interaction, canal: nextcord.TextChannel = None):
            """Obtener ID de un canal"""
            try:
                target_channel = canal or interaction.channel
                
                embed = nextcord.Embed(
                    title="🆔 **ID del Canal**",
                    description=f"Información del canal {target_channel.mention}",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📋 **Información**",
                    value=f"**Nombre:** {target_channel.name}\n**ID:** `{target_channel.id}`\n**Tipo:** {target_channel.type.name}",
                    inline=False
                )
                
                if target_channel.category:
                    embed.add_field(
                        name="📁 **Categoría**",
                        value=f"**Nombre:** {target_channel.category.name}\n**ID:** `{target_channel.category.id}`",
                        inline=False
                    )
                
                embed.set_footer(text="ONZA Bot • Información de Canal")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("ID de Canal Consultado", interaction.user.display_name, f"Canal: {target_channel.name}")
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error obteniendo ID del canal: {str(e)}", ephemeral=True)
                log.error(f"Error en canal_id: {e}")
    
    @nextcord.slash_command(name="moderacion", description="Comandos de moderación automática")
    async def moderacion(self, interaction: nextcord.Interaction):
        """Comando base de moderación"""
        pass
    
    @moderacion.subcommand(name="estado", description="Ver estado del sistema de moderación")
    async def moderacion_estado(self, interaction: nextcord.Interaction):
        """Ver estado del sistema de moderación"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            # Obtener estadísticas de moderación
            from utils import db_query_one, db_query_all
            
            # Total de advertencias
            warnings_result = await db_query_one("SELECT COUNT(*) FROM user_warnings WHERE warnings > 0")
            total_warnings = warnings_result[0] if warnings_result else 0
            
            # Advertencias recientes (últimas 24 horas)
            recent_warnings = await db_query_one(
                "SELECT COUNT(*) FROM moderation_logs WHERE action = 'warning' AND timestamp > ?",
                (datetime.now(timezone.utc).timestamp() - 86400,)
            )
            recent_count = recent_warnings[0] if recent_warnings else 0
            
            # Usuarios con más advertencias
            top_warned = await db_query_all(
                "SELECT user_id, warnings FROM user_warnings WHERE warnings > 0 ORDER BY warnings DESC LIMIT 5"
            )
            
            # Crear embed
            embed = nextcord.Embed(
                title="🛡️ Estado del Sistema de Moderación",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📊 Estadísticas Generales",
                value=f"**Total de advertencias:** {total_warnings}\n**Advertencias (24h):** {recent_count}",
                inline=False
            )
            
            if top_warned:
                top_users = []
                for user_id, warnings in top_warned:
                    user = interaction.guild.get_member(user_id)
                    username = user.display_name if user else f"Usuario {user_id}"
                    top_users.append(f"**{username}:** {warnings} advertencias")
                
                embed.add_field(
                    name="⚠️ Usuarios con más advertencias",
                    value="\n".join(top_users),
                    inline=False
                )
            
            embed.add_field(
                name="🔧 Funciones Activas",
                value="✅ Anti-spam\n✅ Anti-links\n✅ Anti-raid\n✅ Palabras prohibidas",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Moderación Automática")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error obteniendo estado de moderación: {str(e)}", ephemeral=True)
            log.error(f"Error en moderacion_estado: {e}")
    
    @moderacion.subcommand(name="limpiar", description="Limpiar advertencias de un usuario")
    async def moderacion_limpiar(self, interaction: nextcord.Interaction, usuario: nextcord.Member):
        """Limpiar advertencias de un usuario"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            from utils import db_execute
            
            # Limpiar advertencias
            await db_execute(
                "DELETE FROM user_warnings WHERE user_id = ?",
                (usuario.id,)
            )
            
            # Registrar acción
            await db_execute(
                """INSERT INTO moderation_logs (user_id, action, reason, channel_id, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario.id, "warnings_cleared", f"Advertencias limpiadas por {interaction.user.display_name}", 
                 interaction.channel.id, datetime.now(timezone.utc).timestamp())
            )
            
            embed = nextcord.Embed(
                title="✅ Advertencias Limpiadas",
                description=f"Se han limpiado todas las advertencias de **{usuario.display_name}**",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            embed.set_footer(text=f"Acción realizada por {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log de la acción
            await log_accion("Advertencias Limpiadas", interaction.user.display_name, f"Usuario: {usuario.display_name}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error limpiando advertencias: {str(e)}", ephemeral=True)
            log.error(f"Error en moderacion_limpiar: {e}")
