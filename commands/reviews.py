"""
Comandos de reseñas del bot ONZA
"""

from typing import Optional

import nextcord
from nextcord.ext import commands
from nextcord import ui

from config import *
from utils import log, is_staff, log_accion, db_execute, db_query_one, db_query_all
from i18n import t, get_user_lang

class ReviewCommands(commands.Cog):
    """Comandos relacionados con reseñas"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._register_commands()
    
    def _register_commands(self):
        """Registrar comandos de reseñas"""
        
        @self.bot.slash_command(name="reseña", description="Dejar una reseña", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def resena(interaction: nextcord.Interaction, 
                        rating: int = nextcord.SlashOption(description="Calificación (1-5)", min_value=1, max_value=5),
                        comentario: str = nextcord.SlashOption(description="Comentario sobre el servicio", max_length=1000)):
            """Dejar una reseña"""
            try:
                # Verificar que el usuario tenga órdenes
                user_orders = await db_query_all(
                    "SELECT id FROM orders WHERE user_id = ? AND status = 'completed'",
                    (interaction.user.id,)
                )
                
                if not user_orders:
                    await interaction.response.send_message(
                        "❌ Solo puedes dejar reseñas si has completado al menos una compra.",
                        ephemeral=True
                    )
                    return
                
                # Verificar si ya tiene una reseña pendiente
                existing_review = await db_query_one(
                    "SELECT id FROM reviews WHERE user_id = ? AND approved = 0",
                    (interaction.user.id,)
                )
                
                if existing_review:
                    await interaction.response.send_message(
                        "❌ Ya tienes una reseña pendiente de aprobación.",
                        ephemeral=True
                    )
                    return
                
                # Crear reseña
                await db_execute(
                    "INSERT INTO reviews (user_id, order_id, rating, comment, approved, created_at) VALUES (?, ?, ?, ?, 0, datetime('now'))",
                    (interaction.user.id, user_orders[0][0], rating, comentario)
                )
                
                # Crear embed de confirmación
                embed = nextcord.Embed(
                    title="⭐ **Reseña Enviada**",
                    description="Tu reseña ha sido enviada y será revisada por el staff.",
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                
                embed.add_field(
                    name="📊 **Calificación**",
                    value="⭐" * rating,
                    inline=True
                )
                
                embed.add_field(
                    name="💬 **Comentario**",
                    value=comentario[:100] + "..." if len(comentario) > 100 else comentario,
                    inline=False
                )
                
                embed.add_field(
                    name="⏰ **Estado**",
                    value="Pendiente de aprobación",
                    inline=True
                )
                
                embed.set_footer(text=f"{BRAND_NAME} • Sistema de Reseñas")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # Log de la acción
                await log_accion("Reseña Enviada", interaction.user.display_name, f"Rating: {rating}")
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error enviando reseña: {str(e)}", ephemeral=True)
                log.error(f"Error en resena: {e}")
        
        @self.bot.slash_command(name="reseña_aprobar", description="Aprobar reseña (staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
        async def resena_aprobar(interaction: nextcord.Interaction,
                                review_id: Optional[int] = nextcord.SlashOption(description="ID de reseña", required=False),
                                usuario: Optional[nextcord.Member] = nextcord.SlashOption(description="O usuario", required=False)):
            """Aprobar reseña"""
            if not is_staff(interaction.user):
                lang = await get_user_lang(interaction.user.id)
                await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
                return
            
            # Buscar reseña
            if review_id:
                review = await db_query_one("SELECT * FROM reviews WHERE id = ?", (review_id,))
            elif usuario:
                review = await db_query_one(
                    "SELECT * FROM reviews WHERE user_id = ? AND approved = 0 ORDER BY created_at DESC LIMIT 1",
                    (usuario.id,)
                )
            else:
                # Mostrar pendientes
                reviews = await db_query_all(
                    "SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.discord_id WHERE r.approved = 0 LIMIT 10"
                )
                
                if not reviews:
                    await interaction.response.send_message("No hay reseñas pendientes.", ephemeral=True)
                    return
                
                embed = nextcord.Embed(title="📋 Reseñas Pendientes", color=0x00E5A8)
                for r in reviews:
                    embed.add_field(
                        name=f"ID: {r[0]} - {r[10]} - {'⭐' * r[3]}",
                        value=f"{r[4][:100]}...",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not review:
                await interaction.response.send_message("❌ Reseña no encontrada.", ephemeral=True)
                return
            
            # Aprobar
            await db_execute("UPDATE reviews SET approved = 1 WHERE id = ?", (review[0],))
            
            # Publicar en canal
            if REVIEWS_CHANNEL_ID:
                user = self.bot.get_user(review[1])
                product = await db_query_one(
                    "SELECT p.name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?",
                    (review[2],)
                )
                
                embed = nextcord.Embed(
                    title=f"{'⭐' * review[3]} {product[0] if product else 'Producto'}",
                    description=f'"{review[4]}"',
                    color=0x00E5A8,
                    timestamp=nextcord.utils.utcnow()
                )
                embed.set_author(
                    name=user.display_name if user else "Cliente",
                    icon_url=user.avatar.url if user and user.avatar else None
                )
                embed.set_footer(text=f"{BRAND_NAME} • Reseña verificada")
                
                channel = self.bot.get_channel(REVIEWS_CHANNEL_ID)
                if channel:
                    msg = await channel.send(embed=embed)
                    await db_execute(
                        "UPDATE reviews SET posted_message_id = ?, channel_id = ? WHERE id = ?",
                        (msg.id, REVIEWS_CHANNEL_ID, review[0])
                    )
            
            await interaction.response.send_message("✅ Reseña aprobada y publicada.", ephemeral=True)
            
            # Log de la acción
            await log_accion("Reseña Aprobada", interaction.user.display_name, f"Review ID: {review[0]}")
