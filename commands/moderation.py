"""
Comandos de moderación del bot ONZA
"""

import nextcord
from nextcord.ext import commands
from nextcord import ui

from config import *
from utils import log, is_staff, log_accion

class ModerationCommands:
    """Comandos de moderación"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._register_commands()
    
    def _register_commands(self):
        """Registrar comandos de moderación"""
        
        @self.bot.slash_command(name="banear", description="Banear un usuario del servidor (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def banear_usuario(interaction: nextcord.Interaction):
            """Banear un usuario del servidor"""
            if not is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
                return
            
            # Crear modal para banear usuario
            modal = BanearUsuarioModal()
            await interaction.response.send_modal(modal)

class BanearUsuarioModal(ui.Modal):
    """Modal para banear usuario"""
    
    def __init__(self):
        super().__init__(title="Banear Usuario", timeout=300)
        
        self.user_id = ui.TextInput(
            label="ID del Usuario",
            placeholder="Ingresa el ID del usuario a banear...",
            required=True,
            max_length=20
        )
        self.add_item(self.user_id)
        
        self.razon = ui.TextInput(
            label="Razón del baneo",
            placeholder="Ingresa la razón del baneo...",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.razon)
    
    async def callback(self, interaction: nextcord.Interaction):
        """Manejar envío del modal"""
        try:
            # Verificar permisos
            if not interaction.guild.me.guild_permissions.ban_members:
                await interaction.response.send_message("❌ No tengo permisos para banear usuarios.", ephemeral=True)
                return
            
            # Obtener ID del usuario
            try:
                user_id = int(self.user_id.value)
            except ValueError:
                await interaction.response.send_message("❌ ID de usuario inválido.", ephemeral=True)
                return
            
            # Verificar si el usuario ya está baneado
            try:
                ban_entry = await interaction.guild.fetch_ban(nextcord.Object(id=user_id))
                await interaction.response.send_message(f"❌ El usuario <@{user_id}> ya está baneado. Razón: {ban_entry.reason}", ephemeral=True)
                return
            except nextcord.NotFound:
                # Usuario no está baneado, continuar
                pass
            
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="⚠️ **Confirmar Baneo**",
                description=f"¿Estás seguro de que quieres banear al usuario <@{user_id}>?",
                color=0xFF0000,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="👤 **Usuario**",
                value=f"<@{user_id}> (ID: {user_id})",
                inline=False
            )
            
            embed.add_field(
                name="📝 **Razón**",
                value=self.razon.value,
                inline=False
            )
            
            embed.add_field(
                name="👮 **Moderador**",
                value=interaction.user.mention,
                inline=False
            )
            
            embed.set_footer(text="ONZA Bot • Sistema de Moderación")
            
            # Crear view de confirmación
            view = ConfirmarBaneoView(user_id, self.razon.value, interaction.user)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error procesando baneo: {str(e)}", ephemeral=True)
            log.error(f"Error en BanearUsuarioModal: {e}")

class ConfirmarBaneoView(ui.View):
    """View para confirmar baneo"""
    
    def __init__(self, user_id: int, razon: str, moderator: nextcord.Member):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.razon = razon
        self.moderator = moderator
    
    @ui.button(label="✅ Confirmar", style=nextcord.ButtonStyle.danger)
    async def confirmar(self, button: ui.Button, interaction: nextcord.Interaction):
        """Confirmar baneo"""
        try:
            # Verificar que sea el mismo moderador
            if interaction.user != self.moderator:
                await interaction.response.send_message("❌ Solo el moderador que inició el baneo puede confirmarlo.", ephemeral=True)
                return
            
            # Intentar banear al usuario
            try:
                await interaction.guild.ban(
                    nextcord.Object(id=self.user_id),
                    reason=f"{self.razon} | Moderador: {self.moderator.display_name}"
                )
                
                # Crear embed de éxito
                embed = nextcord.Embed(
                    title="✅ **Usuario Baneado**",
                    description=f"El usuario <@{self.user_id}> ha sido baneado exitosamente.",
                    color=0x00FF00,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="👤 **Usuario**",
                    value=f"<@{self.user_id}> (ID: {self.user_id})",
                    inline=False
                )
                
                embed.add_field(
                    name="📝 **Razón**",
                    value=self.razon,
                    inline=False
                )
                
                embed.add_field(
                    name="👮 **Moderador**",
                    value=self.moderator.mention,
                    inline=False
                )
                
                embed.set_footer(text="ONZA Bot • Usuario Baneado")
                
                await interaction.response.edit_message(embed=embed, view=None)
                
                # Log de la acción
                await log_accion("Usuario Baneado", self.moderator.display_name, f"Usuario: {self.user_id}, Razón: {self.razon}")
                
            except nextcord.NotFound:
                await interaction.response.edit_message(
                    content="❌ Usuario no encontrado en el servidor.",
                    embed=None,
                    view=None
                )
            except nextcord.Forbidden:
                await interaction.response.edit_message(
                    content="❌ No tengo permisos para banear a este usuario.",
                    embed=None,
                    view=None
                )
            except Exception as e:
                await interaction.response.edit_message(
                    content=f"❌ Error baneando usuario: {str(e)}",
                    embed=None,
                    view=None
                )
                log.error(f"Error baneando usuario {self.user_id}: {e}")
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error confirmando baneo: {str(e)}", ephemeral=True)
            log.error(f"Error en ConfirmarBaneoView: {e}")
    
    @ui.button(label="❌ Cancelar", style=nextcord.ButtonStyle.secondary)
    async def cancelar(self, button: ui.Button, interaction: nextcord.Interaction):
        """Cancelar baneo"""
        try:
            # Verificar que sea el mismo moderador
            if interaction.user != self.moderator:
                await interaction.response.send_message("❌ Solo el moderador que inició el baneo puede cancelarlo.", ephemeral=True)
                return
            
            embed = nextcord.Embed(
                title="❌ **Baneo Cancelado**",
                description="El baneo ha sido cancelado.",
                color=0xFFA500,
                timestamp=nextcord.utils.utcnow()
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
            # Log de la acción
            await log_accion("Baneo Cancelado", self.moderator.display_name, f"Usuario: {self.user_id}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error cancelando baneo: {str(e)}", ephemeral=True)
            log.error(f"Error en cancelar baneo: {e}")
