"""
Comandos de publicación de mensajes
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion
# from i18n import t, get_user_lang  # Removido - archivo eliminado

class PublicationCommands(commands.Cog):
    """Comandos de publicación de mensajes"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="publicar_bot", description="Publicar mensaje personalizado (solo staff)")
    async def publicar_bot(self, interaction: nextcord.Interaction):
        """Publicar mensaje personalizado"""
        if not is_staff(interaction.user):
            lang = "es"  # Idioma por defecto
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        # Crear modal para el mensaje
        modal = PublicarMensajeModal()
        await interaction.response.send_modal(modal)
    
    @nextcord.slash_command(name="servicios", description="Publicar mensaje de servicios (solo staff)")
    async def servicios(self, interaction: nextcord.Interaction):
        """Publicar mensaje de servicios"""
        if not is_staff(interaction.user):
            lang = "es"  # Idioma por defecto
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        # Crear modal para servicios
        modal = ServiciosModal()
        await interaction.response.send_modal(modal)
    
    @nextcord.slash_command(name="pagos", description="Publicar mensaje de métodos de pago (solo staff)")
    async def pagos(self, interaction: nextcord.Interaction):
        """Publicar mensaje de métodos de pago"""
        if not is_staff(interaction.user):
            lang = "es"  # Idioma por defecto
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        # Crear modal para métodos de pago
        modal = PagosModal()
        await interaction.response.send_modal(modal)

class PublicarMensajeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Publicar Mensaje Personalizado")
        
        self.titulo = nextcord.ui.TextInput(
            label="Título del mensaje",
            placeholder="Ingresa el título...",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.descripcion = nextcord.ui.TextInput(
            label="Descripción",
            placeholder="Ingresa la descripción...",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.descripcion)
        
        self.color = nextcord.ui.TextInput(
            label="Color (hex, ej: #00ff00)",
            placeholder="#00ff00",
            required=False,
            max_length=7
        )
        self.add_item(self.color)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Crear embed
            embed = nextcord.Embed(
                title=self.titulo.value,
                description=self.descripcion.value,
                color=nextcord.Color.green()
            )
            
            # Aplicar color si se especificó
            if self.color.value and self.color.value.startswith('#'):
                try:
                    color_int = int(self.color.value[1:], 16)
                    embed.color = nextcord.Color(color_int)
                except ValueError:
                    pass  # Usar color por defecto si hay error
            
            embed.set_footer(text=f"{BRAND_NAME} • Mensaje Personalizado")
            
            # Enviar mensaje
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Mensaje personalizado publicado.", ephemeral=True)
            
            # Log de la acción
            await log_accion("Mensaje Personalizado", interaction.user.display_name, f"Título: {self.titulo.value}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error publicando mensaje: {str(e)}", ephemeral=True)
            log.error(f"Error en PublicarMensajeModal: {e}")

class ServiciosModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Publicar Mensaje de Servicios")
        
        self.titulo = nextcord.ui.TextInput(
            label="Título",
            placeholder="Nuestros Servicios",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.servicios = nextcord.ui.TextInput(
            label="Lista de servicios",
            placeholder="• Servicio 1\n• Servicio 2\n• Servicio 3",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.servicios)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Crear embed
            embed = nextcord.Embed(
                title=f"🛍️ {self.titulo.value}",
                description=self.servicios.value,
                color=nextcord.Color.blue()
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
            await log_accion("Servicios Publicados", interaction.user.display_name, f"Título: {self.titulo.value}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error publicando servicios: {str(e)}", ephemeral=True)
            log.error(f"Error en ServiciosModal: {e}")

class PagosModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Publicar Métodos de Pago")
        
        self.titulo = nextcord.ui.TextInput(
            label="Título",
            placeholder="Métodos de Pago",
            required=True,
            max_length=256
        )
        self.add_item(self.titulo)
        
        self.metodos = nextcord.ui.TextInput(
            label="Métodos de pago",
            placeholder="• PayPal\n• Transferencia bancaria\n• Criptomonedas",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.metodos)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Crear embed
            embed = nextcord.Embed(
                title=f"💳 {self.titulo.value}",
                description=self.metodos.value,
                color=nextcord.Color.green()
            )
            
            embed.add_field(
                name="ℹ️ **Información**",
                value="Todos los pagos son seguros y procesados de forma confidencial.",
                inline=False
            )
            
            embed.set_footer(text=f"{BRAND_NAME} • Pagos Seguros")
            
            # Enviar mensaje
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Mensaje de métodos de pago publicado.", ephemeral=True)
            
            # Log de la acción
            await log_accion("Métodos de Pago Publicados", interaction.user.display_name, f"Título: {self.titulo.value}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error publicando métodos de pago: {str(e)}", ephemeral=True)
            log.error(f"Error en PagosModal: {e}")

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(PublicationCommands(bot))