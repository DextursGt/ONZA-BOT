"""Tests for loyalty database."""
import pytest
import os
from events.databases.loyalty_db import LoyaltyDatabase


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database creates tables on init."""
    import aiosqlite
    db_path = "/tmp/test_loyalty.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = LoyaltyDatabase(db_path)
    await db.initialize()

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in await cursor.fetchall()]

    assert 'loyalty_points' in tables
    assert 'loyalty_history' in tables

    os.remove(db_path)


@pytest.mark.asyncio
async def test_add_and_get_points():
    """Test adding and getting loyalty points."""
    db_path = "/tmp/test_loyalty2.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = LoyaltyDatabase(db_path)
    await db.initialize()

    await db.add_points(guild_id=111, user_id='999', points=10, reason="invite")
    await db.add_points(guild_id=111, user_id='999', points=5, reason="invite")

    total = await db.get_points(guild_id=111, user_id='999')
    assert total == 15

    os.remove(db_path)


@pytest.mark.asyncio
async def test_leaderboard():
    """Test getting leaderboard."""
    db_path = "/tmp/test_loyalty3.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = LoyaltyDatabase(db_path)
    await db.initialize()

    await db.add_points(guild_id=111, user_id='aaa', points=30, reason="invite")
    await db.add_points(guild_id=111, user_id='bbb', points=10, reason="invite")
    await db.add_points(guild_id=111, user_id='ccc', points=20, reason="invite")

    leaderboard = await db.get_leaderboard(guild_id=111, limit=3)
    assert leaderboard[0]['user_id'] == 'aaa'
    assert leaderboard[1]['user_id'] == 'ccc'
    assert leaderboard[2]['user_id'] == 'bbb'

    os.remove(db_path)
