import nextcord
import requests
import uuid
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List
import json
import aiohttp
import logging
from functools import wraps
import asyncio

# Configuración del sistema de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DiscordBot')
log = logger  # Alias para compatibilidad

# Decorador para reintentos en operaciones críticas
def retry_operation(max_retries: int = 3, delay: float = 1.0):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f'Error en {func.__name__} después de {max_retries} intentos: {str(e)}')
                        raise
                    logger.warning(f'Intento {attempt + 1} fallido para {func.__name__}: {str(e)}')
                    await asyncio.sleep(delay)
            return None
        return wrapper
    return decorator

# Función para enviar notificaciones por DM
async def send_dm_notification(user: nextcord.User, message: str) -> bool:
    try:
        await user.send(message)
        logger.info(f'Notificación enviada a {user.name} (ID: {user.id})')
        return True
    except Exception as e:
        logger.error(f'Error al enviar DM a {user.name} (ID: {user.id}): {str(e)}')
        return False

# Validador de permisos de usuario
def check_user_permissions(user_id: str, required_id: str) -> bool:
    try:
        return str(user_id) == str(required_id)
    except Exception as e:
        logger.error(f'Error en validación de permisos: {str(e)}')
        return False

# Manejador de respuestas de interacción
async def handle_interaction_response(interaction: nextcord.Interaction, message: str, ephemeral: bool = True):
    try:
        await interaction.response.send_message(message, ephemeral=ephemeral)
        logger.debug(f'Respuesta enviada a {interaction.user.name}: {message}')
    except Exception as e:
        logger.error(f'Error al enviar respuesta de interacción: {str(e)}')
        try:
            await interaction.response.send_message(
                "Ha ocurrido un error al procesar tu solicitud.",
                ephemeral=True
            )
        except:
            pass

from config import OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID, FORTNITE_API_URL, FORTNITE_HEADERS
from data_manager import load_data, save_data

def is_owner():
    """Decorador para verificar si el usuario es owner"""
    def decorator(func):
        async def wrapper(interaction, *args, **kwargs):
            role = nextcord.utils.get(interaction.user.roles, id=OWNER_ROLE_ID)
            if role is None:
                await interaction.response.send_message("No tienes permisos para ejecutar este comando. Este comando está reservado para Owners.", ephemeral=True)
                return
            return await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def is_staff(member):
    """Verifica si un miembro es staff (owner, staff o support)"""
    if not member or not hasattr(member, 'roles'):
        return False
    
    staff_roles = [OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID]
    return any(role.id in staff_roles for role in member.roles if role.id)

def log_accion(accion, usuario, detalles=""):
    """Registra una acción en el log"""
    log.info(f"ACCION: {accion} - Usuario: {usuario} - Detalles: {detalles}")

# Funciones de base de datos para compatibilidad
async def db_execute(query, params=None):
    """Ejecuta una consulta SQL"""
    try:
        import aiosqlite
        async with aiosqlite.connect('data/onza_bot.db') as db:
            if params:
                await db.execute(query, params)
            else:
                await db.execute(query)
            await db.commit()
    except Exception as e:
        log.error(f"Error en db_execute: {e}")

async def db_query_one(query, params=None):
    """Ejecuta una consulta SQL y retorna un resultado"""
    try:
        import aiosqlite
        async with aiosqlite.connect('data/onza_bot.db') as db:
            if params:
                cursor = await db.execute(query, params)
            else:
                cursor = await db.execute(query)
            result = await cursor.fetchone()
            return result
    except Exception as e:
        log.error(f"Error en db_query_one: {e}")
        return None

async def db_query_all(query, params=None):
    """Ejecuta una consulta SQL y retorna todos los resultados"""
    try:
        import aiosqlite
        async with aiosqlite.connect('data/onza_bot.db') as db:
            if params:
                cursor = await db.execute(query, params)
            else:
                cursor = await db.execute(query)
            result = await cursor.fetchall()
            return result
    except Exception as e:
        log.error(f"Error en db_query_all: {e}")
        return []

async def setup_error_handlers(bot):
    @bot.event
    async def on_command_error(ctx, error):
        """Maneja errores de comandos"""
        try:
            if isinstance(error, nextcord.ext.commands.MissingPermissions):
                await ctx.send("❌ No tienes permisos para usar este comando.")
            elif isinstance(error, nextcord.ext.commands.CommandNotFound):
                await ctx.send("El comando no existe. Usa !help para ver los comandos disponibles.")
            else:
                await ctx.send("Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo más tarde.")
                logger.error(f"Error en comando {ctx.command}: {str(error)}")
        except Exception as e:
            logger.error(f"Error al manejar error de comando: {e}")

def sync_fortnite_shop():
    """Sincroniza la tienda de Fortnite con la API"""
    data = load_data()
    try:
        response = requests.get(f"{FORTNITE_API_URL}/shop?lang=es", headers=FORTNITE_HEADERS)
        response.raise_for_status()
        shop_data = response.json().get("shop", [])
        
        # Clear previously synced gifts, keep manual ones
        data["gifts"] = {k: v for k, v in data["gifts"].items() if v.get("source") == "manual"}
        
        # Add shop items
        for item in shop_data:
            gift_id = item.get("id", str(uuid.uuid4()))
            data["gifts"][gift_id] = {
                "name": item.get("displayName", "Desconocido"),
                "price": item.get("price", {}).get("finalPrice", 0),
                "image_url": item.get("displayAssets", [{}])[0].get("url", ""),
                "source": "fortnite_api",
                "last_updated": datetime.utcnow().isoformat()
            }
        data["shop"]["last_updated"] = datetime.utcnow().isoformat()
        
        # Guardar en caché
        with open('fortnite_shop_cache.json', 'w', encoding='utf-8') as f:
            json.dump(data["gifts"], f)
            
        save_data(data)
        return True
    except requests.RequestException as e:
        logger.error(f"Error al sincronizar tienda: {e}")
        return False

def cache_fortnite_shop():
    """Obtiene los datos de la tienda desde el caché si están disponibles y son recientes"""
    try:
        with open('fortnite_shop_cache.json', 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            
        # Verificar si los datos en caché son recientes (menos de 1 hora)
        for item in cached_data.values():
            last_updated = datetime.fromisoformat(item.get('last_updated', '2000-01-01'))
            if (datetime.utcnow() - last_updated).total_seconds() > 3600:
                logger.info("Caché de la tienda expirado")
                return None
                
        logger.info("Usando datos en caché de la tienda")
        return cached_data
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Error al leer caché de la tienda: {e}")
        return None