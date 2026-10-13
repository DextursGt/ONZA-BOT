"""
Comandos de moderación
"""

from datetime import timedelta

import aiosqlite
import nextcord
from nextcord.ext import commands

from config import *
from utils import log, is_staff, log_accion
from events.cogs.registro_servidor import enviar_registro

DB_MODERACION = "data/moderacion.db"
MAX_TIMEOUT_MIN = 28 * 24 * 60  # tope de Discord: 28 días
ADVERTENCIAS_A_MOSTRAR = 10


async def _db():
    db = await aiosqlite.connect(DB_MODERACION)
    await db.execute("""CREATE TABLE IF NOT EXISTS advertencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER,
        moderador_id INTEGER, motivo TEXT, creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    return db


async def agregar_advertencia(guild_id: int, user_id: int, moderador_id: int, motivo: str) -> int:
    """Guarda la advertencia y devuelve cuántas lleva el usuario en este servidor."""
    db = await _db()
    try:
        await db.execute("INSERT INTO advertencias (guild_id, user_id, moderador_id, motivo) VALUES (?, ?, ?, ?)",
                         (guild_id, user_id, moderador_id, motivo))
        await db.commit()
        cur = await db.execute("SELECT COUNT(*) FROM advertencias WHERE guild_id = ? AND user_id = ?",
                               (guild_id, user_id))
        return (await cur.fetchone())[0]
    finally:
        await db.close()


async def listar_advertencias(guild_id: int, user_id: int):
    db = await _db()
    try:
        cur = await db.execute("SELECT id, moderador_id, motivo, creado_en FROM advertencias "
                               "WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id))
        return await cur.fetchall()
    finally:
        await db.close()

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

    async def _validar_objetivo(self, interaction: nextcord.Interaction, usuario: nextcord.Member) -> bool:
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return False
        if is_staff(usuario) or usuario.bot:
            await interaction.response.send_message("❌ No se puede usar con staff ni con bots.", ephemeral=True)
            return False
        return True

    @nextcord.slash_command(name="timeout", description="Silenciar temporalmente a un usuario (solo staff)")
    async def timeout(self, interaction: nextcord.Interaction, usuario: nextcord.Member, minutos: int,
                      razon: str = "Sin razón especificada"):
        if not await self._validar_objetivo(interaction, usuario):
            return
        if not 1 <= minutos <= MAX_TIMEOUT_MIN:
            await interaction.response.send_message(
                f"❌ Los minutos van de 1 a {MAX_TIMEOUT_MIN} (28 días).", ephemeral=True)
            return
        try:
            await usuario.edit(timeout=nextcord.utils.utcnow() + timedelta(minutes=minutos),
                               reason=f"{razon} — por {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ No se pudo: {e}", ephemeral=True)
            return
        await interaction.response.send_message(
            f"🔇 {usuario.mention} silenciado {minutos} min. Razón: {razon}", ephemeral=True)
        log_accion("Timeout", interaction.user.display_name, f"{usuario} {minutos} min: {razon}")

    @nextcord.slash_command(name="quitar_timeout", description="Quitar el silencio a un usuario (solo staff)")
    async def quitar_timeout(self, interaction: nextcord.Interaction, usuario: nextcord.Member):
        if not await self._validar_objetivo(interaction, usuario):
            return
        try:
            await usuario.edit(timeout=None, reason=f"Timeout retirado por {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"❌ No se pudo: {e}", ephemeral=True)
            return
        await interaction.response.send_message(f"🔊 {usuario.mention} ya puede escribir.", ephemeral=True)

    @nextcord.slash_command(name="warn", description="Advertir a un usuario; queda en su historial (solo staff)")
    async def warn(self, interaction: nextcord.Interaction, usuario: nextcord.Member, razon: str):
        if not await self._validar_objetivo(interaction, usuario):
            return
        total = await agregar_advertencia(interaction.guild.id, usuario.id, interaction.user.id, razon)
        try:
            await usuario.send(f"⚠️ Recibiste una advertencia en **{interaction.guild.name}**: {razon}")
            aviso_dm = ""
        except Exception:
            aviso_dm = " (no se le pudo mandar DM)"
        await interaction.response.send_message(
            f"⚠️ {usuario.mention} advertido. Lleva **{total}** advertencia(s).{aviso_dm}", ephemeral=True)
        embed = nextcord.Embed(title="⚠️ Advertencia", color=0xFFA500,
                               description=f"{usuario.mention} ({usuario}) — lleva {total}")
        embed.add_field(name="Razón", value=razon[:1000], inline=False)
        embed.add_field(name="Moderador", value=interaction.user.mention)
        await enviar_registro(self.bot, embed)

    @nextcord.slash_command(name="advertencias", description="Ver el historial de advertencias de un usuario (solo staff)")
    async def advertencias(self, interaction: nextcord.Interaction, usuario: nextcord.Member):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        filas = await listar_advertencias(interaction.guild.id, usuario.id)
        if not filas:
            await interaction.response.send_message(f"{usuario.mention} no tiene advertencias.", ephemeral=True)
            return
        lineas = [f"`#{i}` {fecha[:10]} — <@{mod}>: {motivo[:150]}"
                  for i, mod, motivo, fecha in filas[:ADVERTENCIAS_A_MOSTRAR]]
        embed = nextcord.Embed(title=f"Advertencias de {usuario} ({len(filas)})", color=0xFFA500,
                               description="\n".join(lineas))
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            value="• `/timeout` · `/quitar_timeout`\n• `/warn` · `/advertencias`\n• `/limpiar` · `/banear`\n• `/lockdown`",
            inline=False
        )
        
        
        embed.set_footer(text=f"{BRAND_NAME} • Comandos de Moderación")
        
        await ctx.send(embed=embed)

def setup(bot: commands.Bot):
    """Setup del cog"""
    bot.add_cog(ModerationCommands(bot))