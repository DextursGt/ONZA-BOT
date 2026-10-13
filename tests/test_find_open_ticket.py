"""find_open_ticket: no debe bloquear al usuario por tickets cuyo canal ya no existe."""
from commands import tickets


class FakeGuild:
    def __init__(self, channel_ids):
        self.channel_ids = channel_ids

    def get_channel(self, channel_id):
        return object() if channel_id in self.channel_ids else None


def test_ghost_ticket_is_closed_and_live_one_found(monkeypatch):
    data = {"tickets": {
        "ticket-1": {"user_id": "7", "channel_id": "100", "status": "abierto", "estado_detallado": "esperando_revision"},
        "ticket-2": {"user_id": "7", "channel_id": "200", "status": "abierto", "estado_detallado": "esperando_revision"},
        "ticket-3": {"user_id": "8", "channel_id": "300", "status": "abierto", "estado_detallado": "esperando_revision"},
    }}
    saved = []
    monkeypatch.setattr(tickets, "load_data", lambda: data)
    monkeypatch.setattr(tickets, "save_data", lambda d: saved.append(d))

    assert tickets.find_open_ticket(FakeGuild({200, 300}), 7) == "ticket-2"
    assert data["tickets"]["ticket-1"]["status"] == "cerrado"
    assert data["tickets"]["ticket-3"]["status"] == "abierto"
    assert saved

    # Sin canales vivos el usuario ya puede abrir uno nuevo
    assert tickets.find_open_ticket(FakeGuild(set()), 7) is None
