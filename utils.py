import nextcord
import logging
from config import OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID

# Import logger from main module to avoid duplicate configuration
# Logging is configured in main.py
logger = logging.getLogger('onza-bot')
log = logger  # Alias for compatibility

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


# Los comandos de staff solo le APARECEN a quien tiene este permiso (Soporte, Moderador, Owner);
# is_staff() sigue validando en cada comando.
PERMISO_STAFF = nextcord.Permissions(moderate_members=True)


def is_staff(user: nextcord.User) -> bool:
    """Verifica si un miembro es staff (owner, staff o support)"""
    if not user or not hasattr(user, 'roles'):
        return False

    staff_roles = [OWNER_ROLE_ID, STAFF_ROLE_ID, SUPPORT_ROLE_ID]
    return any(role.id in staff_roles for role in user.roles if role.id)

def is_admin(user) -> bool:
    """Owner o staff; el rol de soporte NO cuenta (para comandos destructivos)."""
    if not user or not hasattr(user, 'roles'):
        return False
    return any(role.id in [OWNER_ROLE_ID, STAFF_ROLE_ID] for role in user.roles if role.id)

def log_accion(accion, usuario, detalles=""):
    """Registra una acción en el log"""
    log.info(f"ACCION: {accion} - Usuario: {usuario} - Detalles: {detalles}")

REVIEWS_SCHEMA = """CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, username TEXT, rating INTEGER, comment TEXT,
    status TEXT, created_at TIMESTAMP, approved_by INTEGER, approved_at TIMESTAMP)"""

# Funciones de base de datos para compatibilidad
async def db_execute(query, params=None):
    """Ejecuta una consulta SQL; propaga el error para que quien llama no reporte éxito falso"""
    try:
        import aiosqlite
        async with aiosqlite.connect('data/onza_bot.db') as db:
            await db.execute(REVIEWS_SCHEMA)
            if params:
                await db.execute(query, params)
            else:
                await db.execute(query)
            await db.commit()
    except Exception as e:
        log.error(f"Error en db_execute: {e}")
        raise

async def db_query_one(query, params=None):
    """Ejecuta una consulta SQL y retorna un resultado"""
    try:
        import aiosqlite
        async with aiosqlite.connect('data/onza_bot.db') as db:
            await db.execute(REVIEWS_SCHEMA)
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
            await db.execute(REVIEWS_SCHEMA)
            if params:
                cursor = await db.execute(query, params)
            else:
                cursor = await db.execute(query)
            result = await cursor.fetchall()
            return result
    except Exception as e:
        log.error(f"Error en db_query_all: {e}")
        return []
