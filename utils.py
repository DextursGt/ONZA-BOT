import nextcord
import requests
import uuid
from datetime import datetime
from typing import Callable
import json
import logging
from functools import wraps
import asyncio
from config import OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID

# Import logger from main module to avoid duplicate configuration
# Logging is configured in main.py
logger = logging.getLogger('onza-bot')
log = logger  # Alias for compatibility

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
async def handle_interaction_response(
    interaction: nextcord.Interaction,
    message: str,
    ephemeral: bool = True
) -> None:
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

from config import OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID
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

def is_staff(user: nextcord.User) -> bool:
    """Verifica si un miembro es staff (owner, staff o support)"""
    if not user or not hasattr(user, 'roles'):
        return False

    staff_roles = [OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID]
    return any(role.id in staff_roles for role in user.roles if role.id)

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