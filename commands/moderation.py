"""
Comandos de moderación
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion

class ModerationCommands(commands.Cog):
    """Comandos de moderación"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="banear", description="Banear un usuario (solo staff)")
    async def banear(self, interaction: nextcord.Interaction, usuario: nextcord.Member, razon: str = "Sin razón especificada"):
        """Banear un usuario del servidor"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            # Verificar que no se pueda banear a otro staff
            if is_staff(usuario):
                await interaction.response.send_message("❌ No puedes banear a otro miembro del staff.", ephemeral=True)
                return
            
            # Banear usuario
            await usuario.ban(reason=razon)
            
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="🔨 Usuario Baneado",
                color=nextcord.Color.red(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(name="👤 **Usuario**", value=f"{usuario.mention} ({usuario.name})", inline=True)
            embed.add_field(name="👮 **Moderador**", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 **Razón**", value=razon, inline=False)
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Moderación")
            
            await interaction.response.send_message(embed=embed)
            
            # Log de la acción
            log_accion("Ban", interaction.user.display_name, f"Usuario: {usuario.name}, Razón: {razon}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error baneando usuario: {str(e)}", ephemeral=True)
            log.error(f"Error en banear: {e}")
    
    @nextcord.slash_command(name="limpiar", description="Limpiar mensajes (solo staff)")
    async def limpiar(self, interaction: nextcord.Interaction, cantidad: int = 10):
        """Limpiar mensajes del canal"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        # Limitar la cantidad
        if cantidad > 100:
            cantidad = 100
        elif cantidad < 1:
            cantidad = 1
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Eliminar mensajes
            deleted = await interaction.channel.purge(limit=cantidad)
            
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="🧹 Mensajes Limpiados",
                color=nextcord.Color.green(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(name="📊 **Resultado**", value=f"• **Mensajes eliminados:** {len(deleted)}\n• **Solicitados:** {cantidad}", inline=False)
            embed.add_field(name="👮 **Moderador**", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Moderación")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            log_accion("Limpiar Mensajes", interaction.user.display_name, f"Cantidad: {len(deleted)}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error limpiando mensajes: {str(e)}", ephemeral=True)
            log.error(f"Error en limpiar: {e}")

    @commands.command(name="mod", description="Comandos de moderación")
    async def mod_command(self, ctx):
        """Comando tradicional de moderación"""
        if not is_staff(ctx.author):
            await ctx.send("❌ Solo el staff puede usar este comando.")
            return
        
        embed = nextcord.Embed(
            title="🛡️ Comandos de Moderación",
            description="Comandos disponibles para moderadores:",
            color=0x00FF00,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="🔧 **Comandos Disponibles**",
            value="• `/limpiar` - Limpiar mensajes del canal\n• Otros comandos de moderación disponibles",
            inline=False
        )
        
        embed.add_field(
            name="📊 **Información del Canal**",
            value=f"• **Canal:** {ctx.channel.mention}\n• **Mensajes:** {len(await ctx.channel.history(limit=None).flatten())}",
            inline=False
        )
        
        embed.set_footer(text=f"{BRAND_NAME} • Comandos de Moderación")
        
        await ctx.send(embed=embed)

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(ModerationCommands(bot))