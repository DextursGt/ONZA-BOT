"""
Comandos de usuario del bot ONZA
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
        self._register_commands()
    
    def _register_commands(self):
        """Registrar comandos de usuario"""
        
        @self.bot.slash_command(name="help", description="Ver comandos disponibles", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def help_command(interaction: nextcord.Interaction):
            """Comando de ayuda para usuarios"""
            lang = await get_user_lang(interaction.user.id)
            
            if is_staff(interaction.user):
                # Ayuda para staff
                embed = nextcord.Embed(
                    title="🤖 **Comandos de Staff**",
                    description="Comandos disponibles para el staff:",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📢 **Publicación**",
                    value="`/publicar_bot` - Publicar mensaje personalizado\n`/servicios` - Publicar mensaje de servicios\n`/publicar_metodos_pago` - Publicar métodos de pago visible para todos\n`/actualizar_canales` - Actualizar canales automáticamente",
                    inline=False
                )
                
                embed.add_field(
                    name="⚙️ **Administración**",
                    value="`/actualizar_canales` - Actualizar canales automáticamente\n`/canal_id` - Obtener ID de un canal\n`/limpiar` - Limpiar mensajes del canal\n`/sync_commands` - Sincronizar comandos slash\n`/diagnostico` - Diagnosticar estado del bot\n`/reiniciar_render` - Información para reiniciar Render",
                    inline=False
                )
                
                embed.add_field(
                    name="🔨 **Moderación**",
                    value="`/banear` - Banear un usuario del servidor",
                    inline=False
                )
                
                embed.add_field(
                    name="📊 **Reseñas**",
                    value="`/reseña_aprobar` - Aprobar reseñas de usuarios",
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Comandos de Staff")
                
            else:
                # Ayuda para usuarios normales
                embed = nextcord.Embed(
                    title="🤖 **Comandos de Usuario**",
                    description="Comandos disponibles para todos:",
                    color=0x5865F2,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="🎫 **Tickets**",
                    value="Ve al canal #abrir-ticket y usa el panel de tickets publicado",
                    inline=False
                )
                
                embed.add_field(
                    name="❓ **Información**",
                    value="`/metodos_pago` - Ver métodos de pago disponibles\n`/pagos` - Ver métodos de pago\n`/garantia` - Ver términos de garantía",
                    inline=False
                )
                
                embed.add_field(
                    name="⭐ **Reseñas**",
                    value="`/reseña [rating] [comentario]` - Dejar reseña",
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Comandos de Usuario")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log de la acción
            await log_accion("Help Consultado", interaction.user.display_name, f"Staff: {is_staff(interaction.user)}")
        
        @self.bot.slash_command(name="metodos_pago", description="Ver métodos de pago disponibles", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def metodos_pago(interaction: nextcord.Interaction):
            """Mostrar métodos de pago disponibles"""
            try:
                embed = nextcord.Embed(
                    title="💳 **Métodos de Pago**",
                    description="Aceptamos los siguientes métodos de pago:",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="🪙 **Crypto**",
                    value="• Bitcoin (BTC)\n• Ethereum (ETH)\n• USDT (TRC20/ERC20)",
                    inline=True
                )
                
                embed.add_field(
                    name="💳 **PayPal**",
                    value="• Transferencia directa\n• Pago seguro",
                    inline=True
                )
                
                embed.add_field(
                    name="🏦 **Transferencia**",
                    value="• SPEI\n• OXXO\n• Transferencia bancaria",
                    inline=True
                )
                
                embed.add_field(
                    name="ℹ️ **Información**",
                    value="• Todos los precios están en **MXN**\n• Los pagos se procesan de forma segura\n• Recibirás confirmación en tu ticket",
                    inline=False
                )
                
                embed.set_footer(text=f"{BRAND_NAME} • Métodos de Pago")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Métodos de Pago Consultados", interaction.user.display_name)
                
            except Exception as e:
                await interaction.response.send_message("❌ Error mostrando métodos de pago.", ephemeral=True)
                log.error(f"Error en metodos_pago: {e}")
        
        @self.bot.slash_command(name="pagos", description="Ver métodos de pago disponibles", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def pagos(interaction: nextcord.Interaction):
            """Mostrar métodos de pago (alias de metodos_pago)"""
            # Redirigir al comando metodos_pago
            await metodos_pago(interaction)
        
        @self.bot.slash_command(name="garantia", description="Ver términos de garantía", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def garantia(interaction: nextcord.Interaction):
            """Mostrar términos de garantía"""
            try:
                embed = nextcord.Embed(
                    title="🛡️ **Garantía ONZA**",
                    description="Nuestra garantía te protege:",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="✅ **Verificación Completa**",
                    value="Si ONZA no entrega el servicio prometido, verificamos el caso y procedemos con el reembolso.",
                    inline=False
                )
                
                embed.add_field(
                    name="🔄 **Reembolso Garantizado**",
                    value="100% del dinero de vuelta si no se cumple con el servicio.",
                    inline=False
                )
                
                embed.add_field(
                    name="⏰ **Tiempo de Verificación**",
                    value="24-48 horas para verificar y procesar reembolsos.",
                    inline=False
                )
                
                embed.add_field(
                    name="🔒 **Seguridad Total**",
                    value="Tu información personal solo se maneja dentro del ticket privado.",
                    inline=False
                )
                
                embed.set_footer(text=f"{BRAND_NAME} • Garantía de Calidad")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Garantía Consultada", interaction.user.display_name)
                
            except Exception as e:
                await interaction.response.send_message("❌ Error mostrando garantía.", ephemeral=True)
                log.error(f"Error en garantia: {e}")
