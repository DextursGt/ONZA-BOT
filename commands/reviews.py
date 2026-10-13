"""
Comandos relacionados con reseñas
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion, db_execute, db_query_one
# from i18n import t, get_user_lang  # Removido - archivo eliminado

class ReviewCommands(commands.Cog):
    """Comandos relacionados con reseñas"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="reseña", description="Dejar una reseña")
    async def reseña(self, interaction: nextcord.Interaction):
        """Dejar una reseña del servicio"""
        try:
            # Crear modal para la reseña
            modal = ReseñaModal()
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creando reseña: {str(e)}", ephemeral=True)
            log.error(f"Error en reseña: {e}")
    
    @nextcord.slash_command(name="reseña_aprobar", description="Aprobar una reseña (solo staff)")
    async def reseña_aprobar(self, interaction: nextcord.Interaction, reseña_id: int):
        """Aprobar una reseña pendiente"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        
        try:
            # Buscar la reseña en la base de datos
            reseña = await db_query_one(
                "SELECT * FROM reviews WHERE id = ? AND status = 'pending'",
                (reseña_id,)
            )
            
            if not reseña:
                await interaction.response.send_message("❌ No se encontró una reseña pendiente con ese ID.", ephemeral=True)
                return
            
            # Aprobar la reseña
            await db_execute(
                "UPDATE reviews SET status = 'approved', approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?",
                (interaction.user.id, reseña_id)
            )
            
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="✅ Reseña Aprobada",
                color=nextcord.Color.green(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(name="📝 **Reseña ID**", value=str(reseña_id), inline=True)
            embed.add_field(name="👮 **Aprobada por**", value=interaction.user.mention, inline=True)
            embed.add_field(name="⭐ **Calificación**", value="⭐" * reseña[3], inline=True)
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Reseñas")
            
            await interaction.response.send_message(embed=embed)
            
            # Log de la acción
            log_accion("Reseña Aprobada", interaction.user.display_name, f"ID: {reseña_id}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error aprobando reseña: {str(e)}", ephemeral=True)
            log.error(f"Error en reseña_aprobar: {e}")

class ReseñaModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Dejar una Reseña")
        
        self.calificacion = nextcord.ui.TextInput(
            label="Calificación (1-5)",
            placeholder="5",
            required=True,
            max_length=1
        )
        self.add_item(self.calificacion)
        
        self.comentario = nextcord.ui.TextInput(
            label="Comentario",
            placeholder="Cuéntanos tu experiencia...",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.comentario)
    
    async def callback(self, interaction: nextcord.Interaction):
        try:
            # Validar calificación
            try:
                calificacion = int(self.calificacion.value)
                if calificacion < 1 or calificacion > 5:
                    raise ValueError()
            except ValueError:
                await interaction.response.send_message("❌ La calificación debe ser un número entre 1 y 5.", ephemeral=True)
                return
            
            # Guardar reseña en la base de datos
            await db_execute(
                "INSERT INTO reviews (user_id, username, rating, comment, status, created_at) VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)",
                (interaction.user.id, interaction.user.display_name, calificacion, self.comentario.value)
            )
            
            # Crear embed de confirmación
            embed = nextcord.Embed(
                title="⭐ Reseña Enviada",
                description="¡Gracias por tu reseña! Será revisada por nuestro equipo.",
                color=nextcord.Color.gold(),
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(name="⭐ **Calificación**", value="⭐" * calificacion, inline=True)
            embed.add_field(name="📝 **Comentario**", value=self.comentario.value[:100] + "..." if len(self.comentario.value) > 100 else self.comentario.value, inline=False)
            
            embed.set_footer(text=f"{BRAND_NAME} • Sistema de Reseñas")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log de la acción
            log_accion("Reseña Enviada", interaction.user.display_name, f"Calificación: {calificacion}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error enviando reseña: {str(e)}", ephemeral=True)
            log.error(f"Error en ReseñaModal: {e}")

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(ReviewCommands(bot))