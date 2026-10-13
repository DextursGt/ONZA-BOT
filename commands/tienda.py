"""Acciones de tienda conectadas a onzalatam.com: niveles de cliente, tienda de Fortnite diaria,
precios de Robux en #roblox, y puntos de lealtad."""
import hashlib
import logging
from datetime import datetime, timezone

import nextcord
from nextcord.ext import commands, tasks

import web_api
from config import GUILD_ID, BRAND_NAME
from data_manager import load_data, save_data

log = logging.getLogger('onza-bot')

# Decisión de Alejandro (12-oct-2026): pedidos ENTREGADOS en la web para cada nivel. Acumulativos.
NIVELES_CLIENTE = [(1, "Cliente"), (3, "Cliente LV.1"), (10, "Cliente VIP")]
CATEGORIA_TIENDA = "🛒 Tienda"
CANAL_FORTNITE = "fortnite"
CANAL_ROBLOX = "roblox"
SECCION_SIN_NOMBRE = "Más de la tienda"
MAX_EMBED_DESC = 4000
MAX_EMBEDS_POR_MENSAJE = 10
TOP_RANKING = 10
COLOR = 0x00E5A8


def roles_por_entregados(entregados: int) -> list:
    return [nombre for minimo, nombre in NIVELES_CLIENTE if entregados >= minimo]


async def aplicar_niveles(guild: nextcord.Guild, miembro: nextcord.Member, entregados: int) -> list:
    """Agrega los roles de nivel que le tocan. Nunca quita roles."""
    roles = (nextcord.utils.get(guild.roles, name=n) for n in roles_por_entregados(entregados))
    faltan = [r for r in roles if r and r not in miembro.roles]
    if faltan:
        await miembro.add_roles(*faltan, reason=f"{entregados} pedido(s) entregado(s) en onzalatam.com")
    return faltan


def canal_tienda(guild: nextcord.Guild, nombre: str):
    """#fortnite existe dos veces (Staff y Tienda): siempre el de la categoría Tienda."""
    categoria = nextcord.utils.get(guild.categories, name=CATEGORIA_TIENDA) if guild else None
    return nextcord.utils.get(categoria.text_channels, name=nombre) if categoria else None


def embeds_tienda(tienda: dict) -> list:
    """La tienda agrupada por sección, partida en embeds que caben en Discord."""
    por_seccion = {}
    for a in tienda["articulos"]:
        por_seccion.setdefault(a.get("seccion") or SECCION_SIN_NOMBRE, []).append(a)

    bloques, actual = [], ""
    for seccion, articulos in por_seccion.items():
        texto = f"**{seccion}**\n" + "\n".join(
            f"• {a['nombre']} — {web_api.pesos(a['precioMxn'])}" for a in articulos) + "\n\n"
        if actual and len(actual) + len(texto) > MAX_EMBED_DESC:
            bloques.append(actual)
            actual = ""
        actual += texto[:MAX_EMBED_DESC]
    if actual:
        bloques.append(actual)

    embeds = [nextcord.Embed(description=b, color=COLOR) for b in bloques]
    embeds[0].title = "🛒 Tienda de Fortnite de hoy"
    embeds[0].url = tienda["pagina"]
    embeds[-1].set_footer(text=f"Precios de {tienda['pagina']}")
    return embeds


class TiendaCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.publicar_tienda_fortnite.start()
        self.actualizar_precios_robux.start()

    def cog_unload(self):
        self.publicar_tienda_fortnite.cancel()
        self.actualizar_precios_robux.cancel()

    # ── Tienda de Fortnite: se publica al rotar (00:00 UTC, 18:00 en México) ──────────────
    @tasks.loop(minutes=15)
    async def publicar_tienda_fortnite(self):
        hoy = datetime.now(timezone.utc).date().isoformat()
        previo = load_data().get("tienda_fortnite") or {}
        if previo.get("fecha") == hoy:
            return
        tienda = await web_api.tienda()
        # El cron de la web refresca cada hora: hasta que traiga la de hoy, no se publica la de ayer.
        if not tienda or not tienda.get("articulos") or (tienda.get("actualizadoEn") or "")[:10] != hoy:
            return
        canal = canal_tienda(self.bot.get_guild(GUILD_ID), CANAL_FORTNITE)
        if not canal:
            return
        try:
            embeds = embeds_tienda(tienda)
            ids = []
            for i in range(0, len(embeds), MAX_EMBEDS_POR_MENSAJE):
                ids.append((await canal.send(embeds=embeds[i:i + MAX_EMBEDS_POR_MENSAJE])).id)
            # La de ayer se borra DESPUÉS de publicar la nueva: el canal nunca queda vacío.
            for mensaje_id in previo.get("mensajes", []):
                try:
                    await canal.get_partial_message(mensaje_id).delete()
                except nextcord.NotFound:
                    pass
            data = load_data()
            data["tienda_fortnite"] = {"fecha": hoy, "mensajes": ids}
            save_data(data)
            log.info(f"Tienda de Fortnite publicada: {len(tienda['articulos'])} artículos")
        except Exception as e:
            log.error(f"No se pudo publicar la tienda de Fortnite: {e}")

    # ── Precios de Robux en #roblox: un solo mensaje del bot que se edita si cambian ───────
    @tasks.loop(hours=1)
    async def actualizar_precios_robux(self):
        cat = await web_api.catalogo()
        if not cat or not cat.get("robux"):
            return  # sin precios de la web no se publica nada (nunca cifras viejas)
        canal = canal_tienda(self.bot.get_guild(GUILD_ID), CANAL_ROBLOX)
        if not canal:
            return
        embed = nextcord.Embed(title="🧱 Precios de Robux", color=COLOR,
                               description=web_api.texto_robux(cat, para_ticket=False))
        embed.set_footer(text=f"{BRAND_NAME} • se actualiza solo desde onzalatam.com")
        huella = hashlib.sha1(embed.description.encode()).hexdigest()
        previo = load_data().get("precios_robux") or {}
        try:
            if previo.get("huella") == huella and previo.get("mensaje"):
                return
            mensaje = None
            if previo.get("mensaje"):
                try:
                    mensaje = await canal.fetch_message(previo["mensaje"])
                    await mensaje.edit(embed=embed)
                except nextcord.NotFound:
                    mensaje = None
            if mensaje is None:
                mensaje = await canal.send(embed=embed)
            data = load_data()
            data["precios_robux"] = {"mensaje": mensaje.id, "huella": huella}
            save_data(data)
        except Exception as e:
            log.error(f"No se pudieron actualizar los precios de Robux en #roblox: {e}")

    @publicar_tienda_fortnite.before_loop
    @actualizar_precios_robux.before_loop
    async def _esperar_bot(self):
        await self.bot.wait_until_ready()

    # ── Puntos de lealtad (solo ver; el canje se decide después) ────────────────────────
    @nextcord.slash_command(name="puntos", description="Ver tus puntos de lealtad")
    async def puntos(self, interaction: nextcord.Interaction):
        total = await self.bot.loyalty_db.get_points(interaction.guild.id, str(interaction.user.id))
        await interaction.response.send_message(
            f"⭐ Tienes **{total}** punto(s). Ganas puntos cuando alguien entra al servidor con tu invitación.",
            ephemeral=True)

    @nextcord.slash_command(name="ranking", description="Top de puntos de lealtad del servidor")
    async def ranking(self, interaction: nextcord.Interaction):
        top = await self.bot.loyalty_db.get_leaderboard(interaction.guild.id, limit=TOP_RANKING)
        if not top:
            await interaction.response.send_message("Todavía nadie tiene puntos.", ephemeral=True)
            return
        medallas = {0: "🥇", 1: "🥈", 2: "🥉"}
        lineas = [f"{medallas.get(i, f'`{i + 1}.`')} <@{f['user_id']}> — **{f['total_points']}**"
                  for i, f in enumerate(top)]
        await interaction.response.send_message(embed=nextcord.Embed(
            title="🏆 Ranking de puntos", description="\n".join(lineas), color=COLOR))
