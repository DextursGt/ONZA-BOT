"""Integración con onzalatam.com: precios de Robux y tickets por pedido."""
import asyncio

import web_api
from commands import tickets

CATALOGO = {"robux": {
    "porMillar": 165, "porMillarPaypal": 180,
    "tabla": [{"cantidad": 500, "pesosBase": 80, "pesosPaypal": 87, "esPromo": True},
              {"cantidad": 1000, "pesosBase": 165, "pesosPaypal": 180, "esPromo": False}],
    "grupo": "https://www.roblox.com/communities/1/x", "pagina": "https://onzalatam.com/roblox",
}}


def test_texto_robux_usa_los_precios_de_la_web():
    texto = web_api.texto_robux(CATALOGO)
    assert "$165 por 1,000 RBX" in texto and "$180 con PayPal" in texto
    assert "• 500 RBX: $80 (promo)" in texto and "• 1,000 RBX: $165" in texto
    assert "https://www.roblox.com/communities/1/x" in texto


def test_sin_web_no_inventa_precios():
    texto = web_api.texto_robux(None)
    assert "$" not in texto and "/roblox" in texto


class Canal:
    def __init__(self, id_):
        self.id, self.mensajes = id_, []

    async def send(self, texto):
        self.mensajes.append(texto)


class Guild:
    def __init__(self, miembros):
        self.miembros = miembros

    def get_member(self, id_):
        return object() if id_ in self.miembros else None


def preparar(monkeypatch, data, pedidos, miembros=(111,), crear_ok=True):
    monkeypatch.setattr(tickets, "load_data", lambda: data)
    monkeypatch.setattr(tickets, "save_data", lambda d: None)

    async def pedidos_desde(desde):
        return pedidos
    monkeypatch.setattr(web_api, "pedidos_desde", pedidos_desde)

    canales = {}

    async def crear(guild, miembro, tipo, ctx):
        if not crear_ok:
            return None
        canal = Canal(900 + len(canales))
        canales[canal.id] = canal
        data["tickets"][f"ticket-{canal.id}"] = {"ticket_type": tipo}
        return f"ticket-{canal.id}", canal

    cog = tickets.SimpleTicketCommands.__new__(tickets.SimpleTicketCommands)
    cog._fallos_pedido = {}
    cog._create_ticket = crear
    guild = Guild(set(miembros))
    cog.bot = type("Bot", (), {"get_guild": lambda self, _id: guild,
                               "get_channel": lambda self, id_: canales.get(id_)})()
    return cog, canales


def correr(cog):
    asyncio.run(tickets.SimpleTicketCommands.sincronizar_pedidos_web.coro(cog))


def pedido(id_, estado, cuando, discord="111"):
    return {"id": id_, "idCorto": id_[:8], "estado": estado, "etiqueta": estado.upper(),
            "discordId": discord, "actualizadoEn": cuando}


def test_primera_vuelta_solo_fija_el_cursor(monkeypatch):
    data = {"tickets": {}}
    cog, canales = preparar(monkeypatch, data, [pedido("p1", "pagado", "2026-10-12T10:00:00Z")])
    correr(cog)
    assert data["pedidos_web"]["cursor"] and not canales


def test_pedido_pagado_abre_ticket_y_cada_cambio_se_avisa(monkeypatch):
    data = {"tickets": {}, "pedidos_web": {"cursor": "2026-10-12T00:00:00Z", "vistos": {}}}
    cog, canales = preparar(monkeypatch, data, [pedido("p1", "pagado", "2026-10-12T10:00:00Z")])
    correr(cog)
    (canal,) = canales.values()
    assert canal.mensajes == ["📦 Pedido `p1` — estado: **PAGADO**"]
    assert data["pedidos_web"]["cursor"] == "2026-10-12T10:00:00Z"
    ticket = data["tickets"][data["pedidos_web"]["vistos"]["p1"]["ticket_id"]]
    assert ticket["pedido_estado"] == "pagado"

    cog2, _ = preparar(monkeypatch, data, [pedido("p1", "entregado", "2026-10-12T11:00:00Z")])
    cog2.bot = cog.bot
    correr(cog2)
    assert canal.mensajes[-1] == "📦 Pedido `p1` — estado: **ENTREGADO**" and len(canales) == 1
    assert ticket["pedido_estado"] == "entregado"


def test_cliente_fuera_del_servidor_o_pedido_ya_terminado_no_abre_ticket(monkeypatch):
    data = {"tickets": {}, "pedidos_web": {"cursor": "2026-10-12T00:00:00Z", "vistos": {}}}
    cog, canales = preparar(monkeypatch, data, [
        pedido("p1", "pagado", "2026-10-12T10:00:00Z", discord="222"),
        pedido("p2", "entregado", "2026-10-12T10:01:00Z"),
    ])
    correr(cog)
    assert not canales and set(data["pedidos_web"]["vistos"]) == {"p1", "p2"}


def test_si_no_se_puede_crear_el_ticket_reintenta_y_luego_lo_salta(monkeypatch):
    data = {"tickets": {}, "pedidos_web": {"cursor": "2026-10-12T00:00:00Z", "vistos": {}}}
    cog, _ = preparar(monkeypatch, data, [pedido("p1", "pagado", "2026-10-12T10:00:00Z")], crear_ok=False)
    correr(cog)
    assert data["pedidos_web"]["cursor"] == "2026-10-12T00:00:00Z"  # no avanza: se reintenta
    for _ in range(tickets.MAX_REINTENTOS_PEDIDO - 1):
        correr(cog)
    assert data["pedidos_web"]["cursor"] == "2026-10-12T10:00:00Z"
    assert data["pedidos_web"]["vistos"]["p1"]["ticket_id"] is None


def test_ticket_de_pedido_no_bloquea_abrir_uno_normal(monkeypatch):
    data = {"tickets": {"ticket-1": {"user_id": "7", "channel_id": "100", "status": "abierto",
                                     "estado_detallado": "esperando_revision", "ticket_type": "pedido"}}}
    monkeypatch.setattr(tickets, "load_data", lambda: data)
    monkeypatch.setattr(tickets, "save_data", lambda d: None)
    guild = type("G", (), {"get_channel": lambda self, _id: object()})()
    assert tickets.find_open_ticket(guild, 7) is None
