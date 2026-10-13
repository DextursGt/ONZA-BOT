"""Respaldo diario de data/ (lo corre cron). Copia consistente de las bases SQLite y de los JSON; guarda 7 días.

Uso: python3 scripts/respaldar_datos.py [carpeta_destino]   (por defecto /root/respaldos/onza-bot)
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DIAS_A_GUARDAR = 7


def respaldar(origen: Path, destino_base: Path, hoy: str) -> Path:
    destino = destino_base / hoy
    destino.mkdir(parents=True, exist_ok=True)
    for archivo in origen.iterdir():
        if archivo.suffix == ".db":
            # backup() de SQLite: copia consistente aunque el bot esté escribiendo.
            fuente, copia = sqlite3.connect(archivo), sqlite3.connect(destino / archivo.name)
            try:
                fuente.backup(copia)
            finally:
                fuente.close()
                copia.close()
        elif archivo.suffix == ".json":
            shutil.copy2(archivo, destino / archivo.name)
    for viejo in sorted(p for p in destino_base.iterdir() if p.is_dir())[:-DIAS_A_GUARDAR]:
        shutil.rmtree(viejo)
    return destino


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/respaldos/onza-bot")
    hecho = respaldar(Path(__file__).resolve().parent.parent / "data", base, datetime.now().strftime("%Y-%m-%d"))
    print(f"{datetime.now():%Y-%m-%d %H:%M} respaldo en {hecho}")
