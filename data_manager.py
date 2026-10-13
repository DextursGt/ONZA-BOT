import json
import os
from datetime import datetime
from typing import Dict, Any
from config import DATA_FILE

# Global ticket counter
TICKET_COUNTER = 0

def ensure_data_directory():
    """Asegura que el directorio de datos existe"""
    data_dir = os.path.dirname(DATA_FILE)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)

def load_data() -> Dict[str, Any]:
    """Carga los datos del archivo JSON"""
    global TICKET_COUNTER
    ensure_data_directory()
    
    default_data = {"tickets": {}, "ticket_counter": 0}

    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all keys exist
            for key in default_data:
                if key not in data:
                    data[key] = default_data[key]
            # Sincronizar el contador global con el del archivo
            file_counter = data.get("ticket_counter", 0)
            # Usar el mayor entre el global y el del archivo
            TICKET_COUNTER = max(TICKET_COUNTER, file_counter)
            # Asegurar que el archivo tenga el contador correcto
            data["ticket_counter"] = TICKET_COUNTER
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Guardar aparte un archivo dañado antes de que el siguiente save_data lo pise
        if isinstance(e, json.JSONDecodeError):
            os.replace(DATA_FILE, f"{DATA_FILE}.danado-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        # Si no existe el archivo o hay error, inicializar contador
        TICKET_COUNTER = 0
        return default_data

def save_data(data: Dict[str, Any]) -> bool:
    """Guarda los datos en el archivo JSON"""
    global TICKET_COUNTER
    ensure_data_directory()
    # Asegurar que el contador esté sincronizado
    # Si el contador en data es mayor, actualizar el global
    if "ticket_counter" in data:
        TICKET_COUNTER = max(TICKET_COUNTER, data["ticket_counter"])
    # Siempre guardar el contador global actual
    data["ticket_counter"] = TICKET_COUNTER
    # Escribir a un temporal y renombrar: si el proceso muere a medias, el archivo bueno sigue intacto
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)
    return True

def get_next_ticket_id() -> str:
    """Obtiene el siguiente ID de ticket disponible"""
    global TICKET_COUNTER
    # Cargar datos primero para obtener el contador actual del archivo
    data = load_data()
    # Obtener el contador del archivo (puede ser mayor que el global si se reinició el bot)
    current_counter = data.get("ticket_counter", 0)
    # Usar el mayor entre el global y el del archivo (por si acaso)
    TICKET_COUNTER = max(TICKET_COUNTER, current_counter)
    # Incrementar el contador
    TICKET_COUNTER += 1
    # Actualizar en los datos
    data["ticket_counter"] = TICKET_COUNTER
    # Guardar inmediatamente
    save_data(data)
    return str(TICKET_COUNTER)

