"""Estadísticas por staff y cierre por inactividad."""
import asyncio
from datetime import datetime, timezone, timedelta

import nextcord

from commands import tickets


def iso(dias_atras=0):
    return (datetime.now(timezone.utc) - timedelta(days=dias_atras)).isoformat()


def test_resumen_staff_cuenta_por_persona_y_respeta_periodo():
    data = {
        "t1": {"timestamp": iso(1), "status": "cerrado", "asignado_a": "A", "closed_by": "A"},
        "t2": {"timestamp": iso(2), "status": "completado", "asignado_a": "B", "completed_by": "A"},
        "t3": {"timestamp": iso(60), "status": "cerrado", "closed_by": "B"},  # fuera del periodo
    }
    estados, tomados, completados, cerrados = tickets.resumen_staff(data, datetime.now(timezone.utc) - timedelta(days=30))
    assert estados == {"cerrado": 1, "completado": 1}
    assert tomados == {"A": 1, "B": 1} and completados == {"A": 1} and cerrados == {"A": 1}


class Canal:
    def __init__(self, horas_sin_mensajes, msg_id=111):
        self.last_message_id = nextcord.utils.time_snowflake(
            datetime.now(timezone.utc) - timedelta(hours=horas_sin_mensajes))
        self.enviados, self.borrado = [], False

    async def send(self, texto):
        self.enviados.append(texto)
        msg = type("M", (), {"id": 999})()
        return msg

    async def delete(self, reason=None):
        self.borrado = True


def correr(monkeypatch, ticket, canal):
    data = {"tickets": {"ticket-1": ticket}}
    monkeypatch.setattr(tickets, "load_data", lambda: data)
    monkeypatch.setattr(tickets, "save_data", lambda d: None)
    transcripciones = []

    async def transcribir(c, tid, motivo):
        transcripciones.append(tid)
    monkeypatch.setattr(tickets, "enviar_transcripcion", transcribir)

    cog = tickets.SimpleTicketCommands.__new__(tickets.SimpleTicketCommands)
    cog.bot = type("Bot", (), {"get_channel": lambda self, _id: canal})()
    asyncio.run(tickets.SimpleTicketCommands.revisar_inactivos.coro(cog))
    return data["tickets"]["ticket-1"], transcripciones


def test_avisa_a_las_48h(monkeypatch):
    canal = Canal(horas_sin_mensajes=50)
    t, _ = correr(monkeypatch, {"status": "abierto", "user_id": "7", "channel_id": "1"}, canal)
    assert len(canal.enviados) == 1 and t["aviso_inactividad_msg"] == 999 and not canal.borrado


def test_cierra_24h_despues_del_aviso_con_transcripcion(monkeypatch):
    canal = Canal(horas_sin_mensajes=25)
    aviso = canal.last_message_id  # el último mensaje del canal es el aviso
    t, trans = correr(monkeypatch, {"status": "abierto", "user_id": "7", "channel_id": "1",
                                     "aviso_inactividad_msg": aviso}, canal)
    assert canal.borrado and trans == ["ticket-1"] and t["estado_detallado"] == "cerrado_por_inactividad"


def test_si_alguien_escribe_tras_el_aviso_no_se_cierra(monkeypatch):
    canal = Canal(horas_sin_mensajes=30)
    t, trans = correr(monkeypatch, {"status": "abierto", "user_id": "7", "channel_id": "1",
                                     "aviso_inactividad_msg": 12345}, canal)
    assert not canal.borrado and not trans and t["aviso_inactividad_msg"] is None


def test_pausados_no_se_tocan(monkeypatch):
    canal = Canal(horas_sin_mensajes=500)
    _, trans = correr(monkeypatch, {"status": "pausado", "user_id": "7", "channel_id": "1"}, canal)
    assert not canal.enviados and not canal.borrado
