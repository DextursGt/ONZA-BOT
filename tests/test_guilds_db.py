"""Tests for guilds database."""
import pytest
import aiosqlite
import os
from events.databases.guilds_db import GuildsDatabase

@pytest.mark.asyncio
async def test_database_initialization():
    """Test database creates tables on init."""
    db_path = "/tmp/test_guilds.db"

    # Clean up if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    db = GuildsDatabase(db_path)
    await db.initialize()

    # Verify tables exist
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in await cursor.fetchall()]

    assert 'join_config' in tables
    assert 'leave_config' in tables
    assert 'join_dm_config' in tables
    assert 'auto_roles' in tables
    assert 'verification_config' in tables

    # Clean up
    os.remove(db_path)

@pytest.mark.asyncio
async def test_save_and_get_join_config():
    """Test saving and retrieving join config."""
    db_path = "/tmp/test_guilds.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = GuildsDatabase(db_path)
    await db.initialize()

    # Save config
    config = {
        'guild_id': 1408125343071736009,
        'enabled': True,
        'channel_id': '1414836305300557887',
        'message_template': '¡Bienvenido %member_mention%!',
        'embed_enabled': False
    }
    await db.save_join_config(config)

    # Retrieve config
    retrieved = await db.get_join_config(1408125343071736009)

    assert retrieved is not None
    assert retrieved['enabled'] == 1  # SQLite stores as int
    assert retrieved['channel_id'] == '1414836305300557887'
    assert retrieved['message_template'] == '¡Bienvenido %member_mention%!'

    os.remove(db_path)
