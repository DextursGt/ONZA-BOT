"""
Utility functions for ONZA Bot
Common functions used across the bot
"""
import os
import asyncio
import logging
import json
import time
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import aiosqlite
import nextcord

from config import (
    DATABASE_PATH, BRAND_NAME, STAFF_ROLE_ID, SUPPORT_ROLE_ID,
    CLIENT_ROLE_ID, TICKETS_LOG_CHANNEL_ID, DELIVERIES_LOG_CHANNEL_ID
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onza_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("onza-bot")

def is_staff_or_admin(member: nextcord.Member) -> bool:
    """Verificar si es staff o admin"""
    if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
        return True
    if STAFF_ROLE_ID:
        role = member.guild.get_role(STAFF_ROLE_ID)
        if role and role in member.roles:
            return True
    return False

def is_staff(user) -> bool:
    """Alias para compatibilidad"""
    if isinstance(user, nextcord.Member):
        return is_staff_or_admin(user)
    return False

def generate_order_id() -> str:
    """Generar ID único para orden"""
    return f"ORD-{int(time.time())}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

def generate_ref_code() -> str:
    """Generar código de referido único"""
    return f"{BRAND_NAME}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

async def get_text_channel(guild: nextcord.Guild, ch_id: int) -> Optional[nextcord.TextChannel]:
    """Obtener canal de texto por ID"""
    ch = guild.get_channel(ch_id)
    return ch if isinstance(ch, nextcord.TextChannel) else None

async def upsert_pinned(ch: nextcord.TextChannel, title: str, desc: str, marker: str) -> nextcord.Message:
    """Actualizar o crear mensaje fijado"""
    pins: List[nextcord.Message] = await ch.pins()
    # Buscar por el footer del embed en lugar del contenido
    target = None
    for m in pins:
        if m.author == ch.guild.me and m.embeds:
            embed = m.embeds[0]
            if embed.footer and marker in (embed.footer.text or ""):
                target = m
                break
    
    embed = nextcord.Embed(title=title, description=desc, color=0x00E5A8)
    # Poner el marcador en el footer (menos visible)
    embed.set_footer(text=f"{BRAND_NAME} • {marker}")
    
    if target:
        await target.edit(content=None, embed=embed)
        return target
    msg = await ch.send(embed=embed)
    try:
        await msg.pin()
    except nextcord.Forbidden:
        log.warning("Sin permiso para pin en #%s", ch.name)
    return msg

async def lock_store_channel(ch: nextcord.TextChannel, guild: nextcord.Guild):
    """Bloquear canal para que solo el bot pueda escribir"""
    try:
        ow = ch.overwrites_for(guild.default_role)
        if ow.send_messages is not False:
            ow.send_messages = False
            await ch.set_permissions(guild.default_role, overwrite=ow, reason="Lock canal Tienda")
    except Exception as e:
        log.warning("Permisos no ajustados en #%s: %s", ch.name, e)

async def log_to_channel(channel_id: int, content: str = None, embed: nextcord.Embed = None, bot=None):
    """Enviar log a canal específico"""
    if not channel_id or not bot:
        return
    
    try:
        channel = bot.get_channel(channel_id)
        if channel and isinstance(channel, nextcord.TextChannel):
            await channel.send(content=content, embed=embed)
    except Exception as e:
        log.error(f"Error al enviar log a canal {channel_id}: {e}")

async def ensure_user_exists(user_id: int, username: str = None):
    """Asegurar que el usuario existe en la BD"""
    try:
        existing = await db_query_one("SELECT discord_id FROM users WHERE discord_id = ?", (user_id,))
        if not existing:
            # Generar código de referencia único
            ref_code = generate_ref_code()
            await db_execute(
                "INSERT INTO users (discord_id, username, referral_code) VALUES (?, ?, ?)",
                (user_id, username or str(user_id), ref_code)
            )
            print(f"✅ Usuario creado en BD: {user_id}")
        else:
            print(f"✅ Usuario ya existe en BD: {user_id}")
    except Exception as e:
        print(f"❌ Error en ensure_user_exists: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise e

# Database helpers
async def db_execute(query: str, params: tuple = None):
    """Ejecutar query sin retorno"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        if params:
            await db.execute(query, params)
        else:
            await db.execute(query)
        await db.commit()

async def db_query_one(query: str, params: tuple = None) -> Optional[tuple]:
    """Obtener una fila"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        if params:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()
        else:
            async with db.execute(query) as cursor:
                return await cursor.fetchone()

async def db_query_all(query: str, params: tuple = None) -> List[tuple]:
    """Obtener todas las filas"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        if params:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()
        else:
            async with db.execute(query) as cursor:
                return await cursor.fetchall()

async def ensure_db():
    """Crear base de datos y ejecutar migraciones"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Habilitar foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Primero crear la tabla de migraciones
            migrations_table_sql = """
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            await db.execute(migrations_table_sql)
            await db.commit()
            
            # Obtener última migración aplicada
            async with db.execute("SELECT MAX(version) FROM migrations") as cursor:
                row = await cursor.fetchone()
                last_version = row[0] if row and row[0] else 0
            
            # Aplicar todas las migraciones (excepto la tabla migrations y los índices)
            from config import MIGRATIONS
            migrations_count = len([m for m in MIGRATIONS if not m.startswith("CREATE INDEX")]) - 1
            
            migration_index = 0
            for migration in MIGRATIONS:
                # Saltar la migración de la tabla migrations
                if "CREATE TABLE IF NOT EXISTS migrations" in migration:
                    continue
                    
                migration_index += 1
                
                if migration_index > last_version:
                    try:
                        await db.execute(migration)
                        # Solo registrar migraciones de tablas, no índices
                        if not migration.startswith("CREATE INDEX"):
                            await db.execute("INSERT INTO migrations (version) VALUES (?)", (migration_index,))
                            log.info(f"Migración {migration_index} aplicada")
                    except Exception as e:
                        log.error(f"Error en migración {migration_index}: {e}")
                        log.error(f"SQL: {migration[:100]}...")
                        raise
            
            await db.commit()
            log.info("Base de datos inicializada correctamente")
            
    except Exception as e:
        log.error(f"Error al inicializar base de datos: {e}")
        raise
