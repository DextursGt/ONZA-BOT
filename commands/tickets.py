"""
Comandos relacionados con tickets
"""

import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion
from i18n import t, get_user_lang
from tickets import TicketView

class TicketCommands(commands.Cog):
    """Comandos relacionados con tickets"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @nextcord.slash_command(name="panel", description="Publica el panel de tickets (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
    async def panel(self, interaction: nextcord.Interaction, canal: nextcord.TextChannel = None):
        """Publicar panel de tickets con botones interactivos"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        # Usar canal especificado o canal actual
        target_channel = canal or interaction.channel
        
        # Crear embed del panel
        embed = nextcord.Embed(
            title=f"🎫 Soporte {BRAND_NAME}",
            description="Elige un servicio para abrir tu ticket privado.\n\n**Horario de atención:** 24/7\n**Tiempo de respuesta:** < 50 minutos",
            color=0x00E5A8,
            timestamp=nextcord.utils.utcnow()
        )
        
        embed.add_field(
            name="📋 **Servicios Disponibles**",
            value="• **Compras:** Haz tu pedido\n• **Verificación:** Confirmar tu compra\n• **Garantía:** Reclamar garantía de producto\n• **Otro:** Consultas generales",
            inline=False
        )
        
        embed.add_field(
            name="⚡ **Respuesta Rápida**",
            value="Nuestro equipo te responderá en menos de 50 minutos.",
            inline=False
        )
        
        embed.set_footer(text=f"{BRAND_NAME} • Soporte 24/7")
        
        # Crear vista con botones
        view = TicketView()
        
        # Enviar panel
        await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Panel de tickets publicado en {target_channel.mention}", ephemeral=True)
        
        # Log de la acción
        await log_accion("Panel de Tickets", interaction.user.display_name, f"Canal: {target_channel.name}")
    
    @nextcord.slash_command(name="limpiar_tickets", description="Limpiar tickets cerrados (solo staff)", guild_ids=[GUILD_ID] if GUILD_ID else None)
    async def limpiar_tickets(self, interaction: nextcord.Interaction):
        """Limpiar tickets cerrados automáticamente"""
        if not isinstance(interaction.user, nextcord.Member) or not is_staff(interaction.user):
            lang = await get_user_lang(interaction.user.id)
            await interaction.response.send_message(await t("errors.only_staff", lang), ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Buscar categoría de tickets
            tickets_category = None
            for category in interaction.guild.categories:
                if TICKETS_CATEGORY_NAME.lower() in category.name.lower():
                    tickets_category = category
                    break
            
            if not tickets_category:
                await interaction.followup.send("❌ No se encontró la categoría de tickets.", ephemeral=True)
                return
            
            # Buscar canales cerrados
            closed_channels = []
            for channel in tickets_category.channels:
                if isinstance(channel, nextcord.TextChannel):
                    # Verificar si es un canal de ticket cerrado
                    if "cerrado" in channel.name.lower() or "closed" in channel.name.lower():
                        closed_channels.append(channel)
            
            if not closed_channels:
                await interaction.followup.send("✅ No hay tickets cerrados para limpiar.", ephemeral=True)
                return
            
            # Eliminar canales
            deleted_count = 0
            for channel in closed_channels:
                try:
                    await channel.delete()
                    deleted_count += 1
                except Exception as e:
                    log.error(f"Error eliminando canal {channel.name}: {e}")
            
            # Crear embed de resumen
            embed = nextcord.Embed(
                title="🧹 Limpieza de Tickets Completada",
                color=0x00E5A8,
                timestamp=nextcord.utils.utcnow()
            )
            
            embed.add_field(
                name="📊 **Resumen**",
                value=f"• **Canales encontrados:** {len(closed_channels)}\n• **Canales eliminados:** {deleted_count}\n• **Errores:** {len(closed_channels) - deleted_count}",
                inline=False
            )
            
            embed.set_footer(text="ONZA Bot • Sistema de Limpieza")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log de la acción
            await log_accion("Limpieza de Tickets", interaction.user.display_name, f"Eliminados: {deleted_count}")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error limpiando tickets: {str(e)}", ephemeral=True)
            log.error(f"Error en limpiar_tickets: {e}")