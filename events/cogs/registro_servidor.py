"""Registro del servidor en #registro-servidor y protección anti-raid (lockdown)."""
import logging
import time
from collections import deque
from datetime import datetime, timezone

import nextcord
from utils import PERMISO_STAFF
from nextcord.ext import commands

from config import GUILD_ID, SERVER_LOG_CHANNEL_ID, BRAND_NAME
from data_manager import load_data, save_data
from utils import is_staff

logger = logging.getLogger('onza-bot')

# Anti-raid: con ~240 miembros, 10 entradas en un minuto no es tráfico normal.
UMBRAL_ENTRADAS = 10
VENTANA_ENTRADAS_S = 60
SLOWMODE_LOCKDOWN_S = 30
DIAS_CUENTA_NUEVA = 7
MAX_TEXTO = 1000

COLOR_INFO, COLOR_AVISO, COLOR_PELIGRO = 0x00E5A8, 0xFFA500, 0xFF3B3B


async def enviar_registro(bot, embed: nextcord.Embed, contenido: str = None):
    """Manda un embed a #registro-servidor. Nunca lanza: el registro es un extra."""
    canal = bot.get_channel(SERVER_LOG_CHANNEL_ID) if SERVER_LOG_CHANNEL_ID else None
    if not canal:
        return
    try:
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text=f"{BRAND_NAME} • Registro")
        await canal.send(content=contenido, embed=embed,
                         allowed_mentions=nextcord.AllowedMentions(roles=True, users=False, everyone=False))
    except Exception as e:
        logger.error(f"No se pudo escribir en el registro: {e}")


def _recortar(texto: str) -> str:
    texto = texto or "*(sin texto)*"
    return texto if len(texto) <= MAX_TEXTO else texto[:MAX_TEXTO] + "…"


def canales_publicos(guild: nextcord.Guild):
    """Canales de texto donde @everyone puede escribir (los de tickets quedan fuera solos)."""
    return [c for c in guild.text_channels if c.permissions_for(guild.default_role).send_messages]


async def activar_lockdown(guild: nextcord.Guild, motivo: str) -> bool:
    """Sube la verificación a Alta y pone slowmode en canales públicos. False si ya estaba activo."""
    data = load_data()
    if data.get("lockdown"):
        return False
    previo = {"verification_level": guild.verification_level.value, "slowmode": {}, "motivo": motivo,
              "desde": datetime.now(timezone.utc).isoformat()}
    for canal in canales_publicos(guild):
        previo["slowmode"][str(canal.id)] = canal.slowmode_delay
    # Se guarda ANTES de tocar nada: si el proceso muere a medias, /lockdown off sabe qué restaurar.
    data["lockdown"] = previo
    save_data(data)

    await guild.edit(verification_level=nextcord.VerificationLevel.high, reason=f"Lockdown: {motivo}")
    for canal in canales_publicos(guild):
        await canal.edit(slowmode_delay=SLOWMODE_LOCKDOWN_S, reason=f"Lockdown: {motivo}")
    return True


async def desactivar_lockdown(guild: nextcord.Guild) -> bool:
    data = load_data()
    previo = data.get("lockdown")
    if not previo:
        return False
    await guild.edit(verification_level=nextcord.VerificationLevel(previo["verification_level"]),
                     reason="Fin del lockdown")
    for canal_id, slowmode in previo["slowmode"].items():
        canal = guild.get_channel(int(canal_id))
        if canal:
            await canal.edit(slowmode_delay=slowmode, reason="Fin del lockdown")
    data = load_data()
    data.pop("lockdown", None)
    save_data(data)
    return True


class RegistroServidor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.entradas = deque()

    def _ignorar(self, mensaje) -> bool:
        return (mensaje is None or mensaje.author.bot or mensaje.guild is None
                or mensaje.channel.id == SERVER_LOG_CHANNEL_ID)

    # ── Mensajes ────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: nextcord.RawMessageDeleteEvent):
        mensaje = payload.cached_message
        if self._ignorar(mensaje):
            return  # shortcut: los mensajes fuera de caché (bot recién reiniciado) no se registran
        embed = nextcord.Embed(title="🗑️ Mensaje borrado", color=COLOR_AVISO, description=_recortar(mensaje.content))
        embed.add_field(name="Autor", value=f"{mensaje.author.mention} ({mensaje.author})")
        embed.add_field(name="Canal", value=mensaje.channel.mention)
        if mensaje.attachments:
            embed.add_field(name="Adjuntos", value="\n".join(a.filename for a in mensaje.attachments), inline=False)
        await enviar_registro(self.bot, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, antes: nextcord.Message, despues: nextcord.Message):
        if self._ignorar(antes) or antes.content == despues.content:
            return
        embed = nextcord.Embed(title="✏️ Mensaje editado", color=COLOR_INFO, url=despues.jump_url)
        embed.add_field(name="Antes", value=_recortar(antes.content), inline=False)
        embed.add_field(name="Después", value=_recortar(despues.content), inline=False)
        embed.add_field(name="Autor", value=f"{antes.author.mention} ({antes.author})")
        embed.add_field(name="Canal", value=antes.channel.mention)
        await enviar_registro(self.bot, embed)

    # ── Miembros ────────────────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_update(self, antes: nextcord.Member, despues: nextcord.Member):
        agregados = [r for r in despues.roles if r not in antes.roles]
        quitados = [r for r in antes.roles if r not in despues.roles]
        if agregados or quitados:
            embed = nextcord.Embed(title="🎭 Roles cambiados", color=COLOR_INFO,
                                   description=f"{despues.mention} ({despues})")
            if agregados:
                embed.add_field(name="Agregados", value=", ".join(r.mention for r in agregados))
            if quitados:
                embed.add_field(name="Quitados", value=", ".join(r.mention for r in quitados))
            await enviar_registro(self.bot, embed)
        if antes.communication_disabled_until != despues.communication_disabled_until:
            hasta = despues.communication_disabled_until
            texto = f"hasta <t:{int(hasta.timestamp())}:f>" if hasta else "retirado"
            await enviar_registro(self.bot, nextcord.Embed(
                title="🔇 Timeout", color=COLOR_AVISO, description=f"{despues.mention} ({despues}): {texto}"))

    @commands.Cog.listener()
    async def on_member_join(self, miembro: nextcord.Member):
        dias = (datetime.now(timezone.utc) - miembro.created_at).days
        nueva = dias < DIAS_CUENTA_NUEVA
        embed = nextcord.Embed(title="📥 Entró", color=COLOR_AVISO if nueva else COLOR_INFO,
                               description=f"{miembro.mention} ({miembro})")
        embed.add_field(name="Cuenta creada", value=f"<t:{int(miembro.created_at.timestamp())}:R>"
                        + (" ⚠️ cuenta nueva" if nueva else ""))
        await enviar_registro(self.bot, embed)
        await self._vigilar_raid(miembro.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, miembro: nextcord.Member):
        await enviar_registro(self.bot, nextcord.Embed(
            title="📤 Salió", color=COLOR_INFO, description=f"{miembro.mention} ({miembro})"))

    @commands.Cog.listener()
    async def on_member_ban(self, guild, usuario):
        await enviar_registro(self.bot, nextcord.Embed(
            title="🔨 Baneado", color=COLOR_PELIGRO, description=f"{usuario.mention} ({usuario})"))

    @commands.Cog.listener()
    async def on_member_unban(self, guild, usuario):
        await enviar_registro(self.bot, nextcord.Embed(
            title="♻️ Desbaneado", color=COLOR_INFO, description=f"{usuario.mention} ({usuario})"))

    # ── Anti-raid ───────────────────────────────────────────────────────────────────────
    def registrar_entrada(self, ahora: float) -> bool:
        """True si con esta entrada se cruza el umbral de raid."""
        self.entradas.append(ahora)
        while self.entradas and ahora - self.entradas[0] > VENTANA_ENTRADAS_S:
            self.entradas.popleft()
        return len(self.entradas) >= UMBRAL_ENTRADAS

    async def _vigilar_raid(self, guild: nextcord.Guild):
        if guild.id != GUILD_ID or not self.registrar_entrada(time.monotonic()):
            return
        motivo = f"{UMBRAL_ENTRADAS}+ entradas en {VENTANA_ENTRADAS_S} s"
        try:
            if not await activar_lockdown(guild, motivo):
                return
        except Exception as e:
            logger.error(f"No se pudo activar el lockdown automático: {e}")
            return
        moderador = nextcord.utils.get(guild.roles, name="Moderador")
        await enviar_registro(
            self.bot,
            nextcord.Embed(title="🚨 Posible raid: lockdown activado", color=COLOR_PELIGRO,
                           description=f"{motivo}. Verificación en **Alta** y slowmode de {SLOWMODE_LOCKDOWN_S} s "
                                       f"en canales públicos.\nCuando pase, usa `/lockdown activar:False`."),
            contenido=moderador.mention if moderador else None,
        )

    @nextcord.slash_command(name="lockdown", default_member_permissions=PERMISO_STAFF, description="Activar o quitar el lockdown del servidor (solo staff)",
                            guild_ids=[GUILD_ID])
    async def lockdown(self, interaction: nextcord.Interaction, activar: bool = True):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            if activar:
                hecho = await activar_lockdown(interaction.guild, f"manual por {interaction.user}")
                texto = "🔒 Lockdown activado." if hecho else "Ya había un lockdown activo."
            else:
                hecho = await desactivar_lockdown(interaction.guild)
                texto = "🔓 Lockdown retirado; todo volvió a como estaba." if hecho else "No había lockdown activo."
        except Exception as e:
            logger.error(f"Error en /lockdown: {e}")
            await interaction.followup.send(f"❌ No se pudo: {e}", ephemeral=True)
            return
        await interaction.followup.send(texto, ephemeral=True)
        if hecho:
            await enviar_registro(self.bot, nextcord.Embed(
                title=texto, color=COLOR_PELIGRO if activar else COLOR_INFO,
                description=f"Por {interaction.user.mention}"))


def setup(bot):
    bot.add_cog(RegistroServidor(bot))
