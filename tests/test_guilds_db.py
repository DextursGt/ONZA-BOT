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
