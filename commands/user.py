"""
Comandos disponibles para todos los usuarios
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion
from i18n import t, get_user_lang

class UserCommands(commands.Cog):
    """Comandos disponibles para todos los usuarios"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
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