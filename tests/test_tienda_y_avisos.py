"""Niveles de cliente, tienda de Fortnite, avisos al staff y respaldos."""
import asyncio
import logging
import sqlite3
from collections import deque
from datetime import datetime, timezone

import web_api
from commands import tienda
from events.cogs import avisos_staff
from scripts.respaldar_datos import respaldar


def test_niveles_por_pedidos_entregados():
    assert tienda.roles_por_entregados(0) == []
    assert tienda.roles_por_entregados(1) == ["Cliente"]
    assert tienda.roles_por_entregados(3) == ["Cliente", "Cliente LV.1"]
    assert tienda.roles_por_entregados(10) == ["Cliente", "Cliente LV.1", "Cliente VIP"]


def articulos(n, seccion="Destacados"):
    return [{"nombre": f"Skin {i}", "seccion": seccion, "precioMxn": 93, "precioVbucks": 800} for i in range(n)]


TIENDA = {"pagina": "https://onzalatam.com/fortnite", "actualizadoEn": None, "articulos": []}


def test_embeds_de_tienda_agrupan_y_caben_en_discord():
    embeds = tienda.embeds_tienda({**TIENDA, "articulos": articulos(2) + articulos(1, seccion=None)})
    assert len(embeds) == 1 and "**Destacados**" in embeds[0].description
    assert f"**{tienda.SECCION_SIN_NOMBRE}**" in embeds[0].description and "• Skin 0 — $93" in embeds[0].description

    grandes = tienda.embeds_tienda({**TIENDA, "articulos": articulos(150, "A") + articulos(150, "B")})
    assert len(grandes) > 1 and all(len(e.description) <= tienda.MAX_EMBED_DESC for e in grandes)


class Canal:
    def __init__(self):
        self.enviados, self.borrados = [], []

    async def send(self, embeds=None, embed=None):
        self.enviados.append(embeds or embed)
        return type("M", (), {"id": 500 + len(self.enviados)})()

    def get_partial_message(self, id_):
        canal = self

        class Parcial:
            async def delete(self):
                canal.borrados.append(id_)
        return Parcial()


def correr_tienda(monkeypatch, data, respuesta):
    canal = Canal()
    monkeypatch.setattr(tienda, "load_data", lambda: data)
    monkeypatch.setattr(tienda, "save_data", lambda d: None)
    monkeypatch.setattr(tienda, "canal_tienda", lambda guild, nombre: canal)

    async def falsa():
        return respuesta
    monkeypatch.setattr(web_api, "tienda", falsa)
    cog = tienda.TiendaCommands.__new__(tienda.TiendaCommands)
    cog.bot = type("Bot", (), {"get_guild": lambda self, _id: None})()
    asyncio.run(tienda.TiendaCommands.publicar_tienda_fortnite.coro(cog))
    return canal


def test_no_publica_la_tienda_de_ayer(monkeypatch):
    canal = correr_tienda(monkeypatch, {}, {**TIENDA, "articulos": articulos(3), "actualizadoEn": "2020-01-01T00:05:00Z"})
    assert canal.enviados == []


def test_publica_la_de_hoy_una_vez_y_borra_la_anterior(monkeypatch):
    hoy = datetime.now(timezone.utc).date().isoformat()
    data = {"tienda_fortnite": {"fecha": "2020-01-01", "mensajes": [7]}}
    canal = correr_tienda(monkeypatch, data, {**TIENDA, "articulos": articulos(3), "actualizadoEn": f"{hoy}T00:05:00Z"})
    assert len(canal.enviados) == 1 and canal.borrados == [7]
    assert data["tienda_fortnite"]["fecha"] == hoy

    otra = correr_tienda(monkeypatch, data, {**TIENDA, "articulos": articulos(3), "actualizadoEn": f"{hoy}T01:05:00Z"})
    assert otra.enviados == []  # ya se publicó hoy


def test_precios_robux_para_canal_no_piden_datos():
    cat = {"robux": {"porMillar": 165, "porMillarPaypal": 180, "tabla": [], "grupo": "g", "pagina": "p"}}
    assert "Responde" not in web_api.texto_robux(cat, para_ticket=False)
    assert "Responde" in web_api.texto_robux(cat)


def test_avisos_juntan_errores_y_no_se_avisan_a_si_mismos():
    manejador = avisos_staff.ManejadorErrores()
    for nombre in ("onza-bot", "nextcord.client", avisos_staff.__name__):
        manejador.emit(logging.LogRecord(nombre, logging.ERROR, "", 0, "falló algo", None, None))
    texto = avisos_staff.armar_aviso(manejador.pendientes)
    assert texto.startswith("🔴 2 error(es)") and "`onza-bot` falló algo" in texto
    assert not manejador.pendientes


def test_respaldo_copia_bases_y_json_y_guarda_7_dias(tmp_path):
    datos, destino = tmp_path / "data", tmp_path / "respaldos"
    datos.mkdir()
    con = sqlite3.connect(datos / "loyalty.db")
    con.execute("create table t (x)")
    con.execute("insert into t values (42)")
    con.commit()
    con.close()
    (datos / "bot_data.json").write_text('{"tickets": {}}', encoding="utf-8")
    for dia in range(1, 9):
        (destino / f"2026-01-0{dia}").mkdir(parents=True)

    hecho = respaldar(datos, destino, "2026-10-12")
    copia = sqlite3.connect(hecho / "loyalty.db")
    assert copia.execute("select x from t").fetchone() == (42,)
    copia.close()
    assert (hecho / "bot_data.json").exists()
    dias = sorted(p.name for p in destino.iterdir())
    assert len(dias) == 7 and dias[-1] == "2026-10-12"
