import json
import os
from datetime import datetime
from config import DATA_FILE

# Global ticket counter
TICKET_COUNTER = 0

def ensure_data_directory():
    """Asegura que el directorio de datos existe"""
    data_dir = os.path.dirname(DATA_FILE)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)

def load_data():
    """Carga los datos del archivo JSON"""
    global TICKET_COUNTER
    ensure_data_directory()
    
    default_data = {
        "users": {},
        "products": {},
        "categories": {},  
        "tickets": {},
        "ticket_counter": 0,
        "payment_info": {
            "Transferencia": "CLABE: 123456789012345678 (Banco: Ejemplo)",
            "PayPal": "Correo: pagos@ejemplo.com",
            "Depósito Oxxo": "Número de cuenta: 9876543210 (Referencia: 12345)"
        },
        "gifts": {},
        "shop": {"last_updated": ""},
        "roblox_accounts": {},
        "pending_verifications": {},
        "reminded_users": [],
        "economy": {
            "users": {},
            "global_stats": {
                "total_coins_in_circulation": 0,
                "total_games_played": 0,
                "total_jobs_completed": 0
            }
        }
    }
    
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all keys exist
            for key in default_data:
                if key not in data:
                    data[key] = default_data[key]
            TICKET_COUNTER = data.get("ticket_counter", 0)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def save_data(data):
    """Guarda los datos en el archivo JSON"""
    global TICKET_COUNTER
    ensure_data_directory()
    data["ticket_counter"] = TICKET_COUNTER
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_next_ticket_id():
    """Obtiene el siguiente ID de ticket disponible"""
    global TICKET_COUNTER
    TICKET_COUNTER += 1
    data = load_data()
    data["ticket_counter"] = TICKET_COUNTER
    save_data(data)
    return TICKET_COUNTER

def update_product_availability(product_id, is_available):
    """Actualiza la disponibilidad de un producto"""
    data = load_data()
    if product_id in data["products"]:
        data["products"][product_id]["available"] = is_available
        save_data(data)
        return True
    return False

def get_category_by_id(category_id: str):
    """Obtiene una categoría por su ID"""
    data = load_data()
    return data['categories'].get(category_id)

def get_all_categories():
    """Obtiene todas las categorías"""
    data = load_data()
    return data['categories']

def add_category(name: str, description: str = "", icon: str = ""):
    """Añade una nueva categoría y retorna su ID"""
    data = load_data()
    category_id = str(len(data['categories']) + 1)
    
    data['categories'][category_id] = {
        "name": name,
        "description": description,
        "icon": icon,
        "created_at": datetime.utcnow().isoformat(),
        "products": []
    }
    
    save_data(data)
    return category_id

def update_category(category_id: str, name: str = None, description: str = None, icon: str = None):
    """Actualiza una categoría existente"""
    data = load_data()
    if category_id not in data['categories']:
        return False
        
    if name is not None:
        data['categories'][category_id]['name'] = name
    if description is not None:
        data['categories'][category_id]['description'] = description
    if icon is not None:
        data['categories'][category_id]['icon'] = icon
        
    save_data(data)
    return True

def delete_category(category_id: str):
    """Elimina una categoría y actualiza los productos asociados"""
    data = load_data()
    if category_id not in data['categories']:
        return False
        
    # Eliminar la categoría de todos los productos asociados
    for product_id in data['categories'][category_id]['products']:
        if product_id in data['products']:
            data['products'][product_id]['category_id'] = None
            
    del data['categories'][category_id]
    save_data(data)
    return True

def assign_product_to_category(product_id: str, category_id: str):
    """Asigna un producto a una categoría"""
    data = load_data()
    if product_id not in data['products'] or category_id not in data['categories']:
        return False
        
    # Remover el producto de su categoría actual si tiene una
    current_category_id = data['products'][product_id].get('category_id')
    if current_category_id and current_category_id in data['categories']:
        data['categories'][current_category_id]['products'].remove(product_id)
        
    # Asignar el producto a la nueva categoría
    data['products'][product_id]['category_id'] = category_id
    if product_id not in data['categories'][category_id]['products']:
        data['categories'][category_id]['products'].append(product_id)
        
    save_data(data)
    return True

# Funciones para manejar cuentas de Roblox
def get_roblox_account(discord_user_id: str):
    """Obtiene la cuenta de Roblox vinculada a un usuario de Discord"""
    data = load_data()
    return data.get('roblox_accounts', {}).get(discord_user_id)

def link_roblox_account(discord_user_id: str, roblox_data: dict):
    """Vincula una cuenta de Roblox a un usuario de Discord"""
    data = load_data()
    if 'roblox_accounts' not in data:
        data['roblox_accounts'] = {}
    
    data['roblox_accounts'][discord_user_id] = roblox_data
    save_data(data)
    return True

def unlink_roblox_account(discord_user_id: str):
    """Desvincula una cuenta de Roblox de un usuario de Discord"""
    data = load_data()
    if 'roblox_accounts' in data and discord_user_id in data['roblox_accounts']:
        del data['roblox_accounts'][discord_user_id]
        save_data(data)
        return True
    return False

def get_pending_verification(discord_user_id: str):
    """Obtiene una verificación pendiente para un usuario"""
    data = load_data()
    return data.get('pending_verifications', {}).get(discord_user_id)

def add_pending_verification(discord_user_id: str, verification_data: dict):
    """Añade una verificación pendiente para un usuario"""
    data = load_data()
    if 'pending_verifications' not in data:
        data['pending_verifications'] = {}
    
    data['pending_verifications'][discord_user_id] = verification_data
    save_data(data)
    return True

def remove_pending_verification(discord_user_id: str):
    """Remueve una verificación pendiente para un usuario"""
    data = load_data()
    if 'pending_verifications' in data and discord_user_id in data['pending_verifications']:
        del data['pending_verifications'][discord_user_id]
        save_data(data)
        return True
    return False

def get_all_roblox_accounts():
    """Obtiene todas las cuentas de Roblox vinculadas"""
    data = load_data()
    return data.get('roblox_accounts', {})

def cleanup_expired_verifications():
    """Limpia las verificaciones expiradas"""
    data = load_data()
    if 'pending_verifications' not in data:
        return 0
    
    current_time = datetime.utcnow()
    expired_keys = []
    
    for user_id, verification in data['pending_verifications'].items():
        try:
            expires_at = datetime.fromisoformat(verification['expires_at'])
            if current_time > expires_at:
                expired_keys.append(user_id)
        except:
            # Si hay error al parsear la fecha, considerar como expirado
            expired_keys.append(user_id)
    
    for key in expired_keys:
        del data['pending_verifications'][key]
    
    if expired_keys:
        save_data(data)
    
    return len(expired_keys)
