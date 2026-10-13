"""Avisos al staff en #deploy-log: cuándo arranca el bot (qué versión) y los errores del último minuto.

Si el proceso muere, PM2 lo levanta y el aviso de arranque lo delata; antes nadie se enteraba.
"""
import logging
import subprocess
from collections import deque

import nextcord
from nextcord.ext import commands, tasks

from config import GUILD_ID

CANAL_AVISOS = "deploy-log"
MAX_PENDIENTES = 50
MAX_LARGO_ERROR = 300
MAX_MENSAJE = 1990


def version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or "?"
    except Exception:
        return "?"


class ManejadorErrores(logging.Handler):
    """Junta los ERROR de cualquier logger para mandarlos en un solo mensaje por minuto."""

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.pendientes = deque(maxlen=MAX_PENDIENTES)

    def emit(self, record):
        if record.name == __name__:
            return  # un fallo al avisar no se vuelve a avisar
        self.pendientes.append(f"`{record.name}` {record.getMessage()[:MAX_LARGO_ERROR]}")


def armar_aviso(pendientes: deque) -> str:
    lineas = []
    while pendientes:
        lineas.append(pendientes.popleft())
    return f"🔴 {len(lineas)} error(es) en el último minuto:\n" + "\n".join(lineas)


class AvisosStaff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manejador = ManejadorErrores()
        logging.getLogger().addHandler(self.manejador)
        self.arranque_avisado = False
        self.enviar_avisos.start()

    def cog_unload(self):
        logging.getLogger().removeHandler(self.manejador)
        self.enviar_avisos.cancel()

    @tasks.loop(minutes=1)
    async def enviar_avisos(self):
        guild = self.bot.get_guild(GUILD_ID)
        canal = nextcord.utils.get(guild.text_channels, name=CANAL_AVISOS) if guild else None
        if not canal:
            return
        try:
            if not self.arranque_avisado:
                self.arranque_avisado = True
                await canal.send(f"🟢 Bot en línea — versión `{version()}`")
            if self.manejador.pendientes:
                await canal.send(armar_aviso(self.manejador.pendientes)[:MAX_MENSAJE])
        except Exception as e:
            logging.getLogger(__name__).warning(f"No se pudo avisar en #{CANAL_AVISOS}: {e}")

    @enviar_avisos.before_loop
    async def _esperar_bot(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(AvisosStaff(bot))
