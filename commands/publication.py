"""
Comandos de publicación del bot ONZA
"""

import nextcord
from nextcord.ext import commands
from nextcord import ui

from config import *
from utils import log, is_staff, log_accion
from i18n import t, get_user_lang

class PublicationCommands:
    """Comandos de publicación de mensajes"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._register_commands()
    
    def _register_commands(self):
        """Registrar comandos de publicación"""
        
        @self.bot.slash_command(name="publicar_bot", description="Publicar mensaje personalizado (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def publicar_bot(interaction: nextcord.Interaction):
            """Publicar mensaje personalizado"""
            if not is_staff(interaction.user):
                lang = await get_user_lang(interaction.user.id)
                await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
                return
            
            # Crear modal para el mensaje
            modal = PublicarMensajeModal()
            await interaction.response.send_modal(modal)
        
        @self.bot.slash_command(name="servicios", description="Publicar mensaje de servicios (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def servicios(interaction: nextcord.Interaction):
            """Publicar mensaje de servicios"""
            if not is_staff(interaction.user):
                lang = await get_user_lang(interaction.user.id)
                await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
                return
            
            # Crear modal para servicios
            modal = ServiciosModal()
            await interaction.response.send_modal(modal)
        
        @self.bot.slash_command(name="publicar_metodos_pago", description="Publicar métodos de pago visible para todos (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def publicar_metodos_pago(interaction: nextcord.Interaction):
            """Publicar métodos de pago como mensaje visible para todos los usuarios"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            try:
                # Crear embed de métodos de pago
                embed = nextcord.Embed(
                    title="💳 **Métodos de Pago ONZA**",
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
                
                # Enviar mensaje y fijarlo
                message = await interaction.channel.send(embed=embed)
                await message.pin()
                
                await interaction.response.send_message("✅ Métodos de pago publicados y fijados.", ephemeral=True)
                
                # Log de la acción
                await log_accion("Métodos de Pago Publicados", interaction.user.display_name, f"Canal: {interaction.channel.name}")
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error publicando métodos de pago: {str(e)}", ephemeral=True)
                log.error(f"Error en publicar_metodos_pago: {e}")

class PublicarMensajeModal(ui.Modal):
    """Modal para publicar mensaje personalizado"""
    
    def __init__(self):
        super().__init__(title="Publicar Mensaje", timeout=300)
        
        self.titulo = ui.TextInput(
            label="Título del mensaje",
            placeholder="Ingresa el título...",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.descripcion = ui.TextInput(
            label="Descripción",
            placeholder="Ingresa la descripción...",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            max_length=4000
        )
        self.add_item(self.descripcion)
        
        self.color = ui.TextInput(
            label="Color (hex, opcional)",
            placeholder="Ej: 00E5A8",
            required=False,
            max_length=6
        )
        self.add_item(self.color)
    
    async def callback(self, interaction: nextcord.Interaction):
        """Manejar envío del modal"""
        try:
            # Procesar color
            color = 0x00E5A8  # Color por defecto
            if self.color.value:
                try:
                    color = int(self.color.value, 16)
                except ValueError:
                    color = 0x00E5A8
            
            # Crear embed
            embed = nextcord.Embed(
                title=self.titulo.value,
                description=self.descripcion.value,
                color=color,
                timestamp=nextcord.utils.utcnow()
            )
            embed.set_footer(text=f"{BRAND_NAME} • Mensaje Personalizado")
            
            # Enviar mensaje
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Mensaje publicado correctamente.", ephemeral=True)
            
            # Log de la acción
            from utils import log_accion
            await log_accion("Mensaje Publicado", interaction.user.display_name, f"Título: {self.titulo.value}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error publicando mensaje: {str(e)}", ephemeral=True)
            log.error(f"Error en PublicarMensajeModal: {e}")

class ServiciosModal(ui.Modal):
    """Modal para publicar mensaje de servicios"""
    
    def __init__(self):
        super().__init__(title="Publicar Servicios", timeout=300)
        
        self.titulo = ui.TextInput(
            label="Título",
            placeholder="Ej: Servicios ONZA",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.descripcion = ui.TextInput(
            label="Descripción",
            placeholder="Describe los servicios disponibles...",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            max_length=4000
        )
        self.add_item(self.descripcion)
    
    async def callback(self, interaction: nextcord.Interaction):
        """Manejar envío del modal"""
        try:
            # Crear embed
            embed = nextcord.Embed(
                title=self.titulo.value,
                description=self.descripcion.value,
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="🛒 **¿Cómo comprar?**",
                value="1. Ve al canal de tickets\n2. Abre un ticket\n3. Especifica qué necesitas\n4. Realiza el pago\n5. Recibe tu servicio",
                inline=False
            )
            
            embed.add_field(
                name="🎫 **Abrir Ticket**",
                value="Puedes abrir tu ticket en el canal de tickets usando el panel disponible.",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Servicios Premium")
            
            # Enviar mensaje y fijarlo
            message = await interaction.channel.send(embed=embed)
            await message.pin()
            
            await interaction.response.send_message("✅ Mensaje de servicios publicado y fijado.", ephemeral=True)
            
            # Log de la acción
            from utils import log_accion
            await log_accion("Servicios Publicados", interaction.user.display_name, f"Título: {self.titulo.value}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error publicando servicios: {str(e)}", ephemeral=True)
            log.error(f"Error en ServiciosModal: {e}")
