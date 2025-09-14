"""
Comandos disponibles para todos los usuarios
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion

class UserCommands(commands.Cog):
    """Comandos disponibles para todos los usuarios"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(name="help", description="Mostrar ayuda del bot")
    async def help_command(self, ctx):
        """Mostrar información de ayuda del bot"""
        try:
            # Crear embed de ayuda
            embed = nextcord.Embed(
                title=f"🤖 {BRAND_NAME} Bot - Ayuda",
                description="Aquí tienes información sobre cómo usar el bot:",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="🎫 **Sistema de Tickets**",
                value="• `!panel` - Mostrar panel de tickets\n• `!ticket` - Crear ticket directamente\n• `!limpiar_tickets` - Limpiar todos los tickets (solo staff)",
                inline=False
            )
            
            embed.add_field(
                name="👑 **Comandos de Staff**",
                value="• `!admin` - Comandos de administración\n• `!mod` - Comandos de moderación\n• `!limpiar_tickets` - Limpiar sistema de tickets",
                inline=False
            )
            
            embed.add_field(
                name="📝 **Comandos Generales**",
                value="• `!help` - Mostrar esta ayuda\n• `!reseña` - Dejar una reseña\n• `!panel` - Panel de tickets",
                inline=False
            )
            
            embed.add_field(
                name="🔧 **Comandos de Moderación**",
                value="• `!limpiar` - Limpiar mensajes del canal\n• `!kick` - Expulsar usuario\n• `!ban` - Banear usuario",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ **Comandos de Administración**",
                value="• `!sync_commands` - Sincronizar comandos slash\n• `!diagnostico` - Diagnóstico del bot\n• `!reiniciar_bot` - Reiniciar el bot",
                inline=False
            )
            
            embed.add_field(
                name="🔧 **Información del Bot**",
                value=f"• **Servidores:** {len(self.bot.guilds)}\n• **Usuarios:** {len(self.bot.users)}\n• **Latencia:** {round(self.bot.latency * 1000)}ms",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Soporte 24/7")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error mostrando ayuda: {str(e)}")
            log.error(f"Error en help: {e}")

    @nextcord.slash_command(name="help", description="Mostrar ayuda del bot")
    async def help(self, interaction: nextcord.Interaction):
        """Mostrar información de ayuda del bot"""
        try:
            # Crear embed de ayuda
            embed = nextcord.Embed(
                title=f"🤖 {BRAND_NAME} Bot - Ayuda",
                description="Aquí tienes información sobre cómo usar el bot:",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="🎫 **Tickets**",
                value="• Usa `/panel` para abrir un ticket\n• Ve al canal #abrir-ticket y usa el panel de tickets publicado",
                inline=False
            )
            
            embed.add_field(
                name="🛍️ **Servicios**",
                value="• Usa `/servicios` para ver nuestros servicios\n• Usa `/pagos` para ver métodos de pago",
                inline=False
            )
            
            embed.add_field(
                name="⭐ **Reseñas**",
                value="• Usa `/reseña` para dejar una reseña\n• Las reseñas ayudan a otros usuarios",
                inline=False
            )
            
            embed.add_field(
                name="🔧 **Staff**",
                value="• Los comandos de staff están disponibles solo para el equipo\n• Contacta al staff si necesitas ayuda",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Soporte 24/7")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error mostrando ayuda: {str(e)}", ephemeral=True)
            log.error(f"Error en help: {e}")

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(UserCommands(bot))