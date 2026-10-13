"""Anti-raid, lockdown reversible y advertencias."""
import asyncio

import nextcord

from commands import moderation
from events.cogs import registro_servidor as rs


def test_umbral_de_raid_solo_cuenta_la_ventana():
    cog = rs.RegistroServidor.__new__(rs.RegistroServidor)
    cog.entradas = __import__("collections").deque()
    # Entradas espaciadas más que la ventana nunca disparan.
    assert not any(cog.registrar_entrada(i * (rs.VENTANA_ENTRADAS_S + 1)) for i in range(rs.UMBRAL_ENTRADAS * 2))
    cog.entradas.clear()
    disparos = [cog.registrar_entrada(1000 + i) for i in range(rs.UMBRAL_ENTRADAS)]
    assert disparos[-1] and not any(disparos[:-1])


class Canal:
    def __init__(self, id_, slowmode, publico=True):
        self.id, self.slowmode_delay, self.publico = id_, slowmode, publico

    def permissions_for(self, _rol):
        return type("P", (), {"send_messages": self.publico})()

    async def edit(self, slowmode_delay, reason=None):
        self.slowmode_delay = slowmode_delay


class Guild:
    def __init__(self):
        self.verification_level = nextcord.VerificationLevel.medium
        self.default_role = object()
        self.canales = [Canal(1, 0), Canal(2, 5), Canal(3, 0, publico=False)]

    @property
    def text_channels(self):
        return self.canales

    def get_channel(self, id_):
        return next(c for c in self.canales if c.id == id_)

    async def edit(self, verification_level, reason=None):
        self.verification_level = verification_level


def test_lockdown_se_activa_una_vez_y_se_revierte_exacto(monkeypatch):
    data = {}
    monkeypatch.setattr(rs, "load_data", lambda: data)
    monkeypatch.setattr(rs, "save_data", lambda d: None)
    g = Guild()

    assert asyncio.run(rs.activar_lockdown(g, "prueba"))
    assert g.verification_level == nextcord.VerificationLevel.high
    assert [c.slowmode_delay for c in g.canales] == [rs.SLOWMODE_LOCKDOWN_S, rs.SLOWMODE_LOCKDOWN_S, 0]
    assert not asyncio.run(rs.activar_lockdown(g, "otra vez"))  # no pisa el estado guardado

    assert asyncio.run(rs.desactivar_lockdown(g))
    assert g.verification_level == nextcord.VerificationLevel.medium
    assert [c.slowmode_delay for c in g.canales] == [0, 5, 0]
    assert "lockdown" not in data and not asyncio.run(rs.desactivar_lockdown(g))


def test_advertencias_se_acumulan_por_usuario(tmp_path, monkeypatch):
    monkeypatch.setattr(moderation, "DB_MODERACION", str(tmp_path / "mod.db"))

    async def flujo():
        assert await moderation.agregar_advertencia(1, 7, 99, "spam") == 1
        assert await moderation.agregar_advertencia(1, 7, 99, "insultos") == 2
        assert await moderation.agregar_advertencia(1, 8, 99, "otro") == 1
        return await moderation.listar_advertencias(1, 7)

    filas = asyncio.run(flujo())
    assert [f[2] for f in filas] == ["insultos", "spam"]
