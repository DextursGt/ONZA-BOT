"""Guardado atómico de bot_data.json y tabla de reseñas."""
import asyncio
import json

import data_manager
import utils


def test_save_es_atomico_y_json_danado_se_respalda(tmp_path, monkeypatch):
    archivo = tmp_path / "bot_data.json"
    monkeypatch.setattr(data_manager, "DATA_FILE", str(archivo))

    data_manager.save_data({"tickets": {"ticket-1": {}}, "ticket_counter": 1})
    assert json.loads(archivo.read_text(encoding="utf-8"))["tickets"] == {"ticket-1": {}}
    assert not (tmp_path / "bot_data.json.tmp").exists()

    archivo.write_text("{roto", encoding="utf-8")
    assert data_manager.load_data()["tickets"] == {}
    respaldos = list(tmp_path.glob("bot_data.json.danado-*"))
    assert len(respaldos) == 1 and respaldos[0].read_text(encoding="utf-8") == "{roto"


def test_resena_se_guarda_y_se_lee(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()

    async def flujo():
        await utils.db_execute(
            "INSERT INTO reviews (user_id, username, rating, comment, status, created_at) "
            "VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)", (7, "ana", 5, "excelente"))
        return await utils.db_query_one("SELECT * FROM reviews WHERE id = ? AND status = 'pending'", (1,))

    fila = asyncio.run(flujo())
    assert fila[3] == 5  # reviews.py lee la calificación en el índice 3
