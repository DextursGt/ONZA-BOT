"""Tests for invites database."""
import pytest
import aiosqlite
import os
from events.databases.invites_db import InvitesDatabase


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database creates tables on init."""
    db_path = "/tmp/test_invites.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = InvitesDatabase(db_path)
    await db.initialize()

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in await cursor.fetchall()]

    assert 'invite_codes' in tables
    assert 'invite_uses' in tables

    os.remove(db_path)


@pytest.mark.asyncio
async def test_save_and_get_invite():
    """Test saving and retrieving invite code."""
    db_path = "/tmp/test_invites2.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = InvitesDatabase(db_path)
    await db.initialize()

    await db.save_invite(
        guild_id=111,
        code="abc123",
        inviter_id="999",
        uses=0
    )

    invite = await db.get_invite(guild_id=111, code="abc123")
    assert invite is not None
    assert invite['inviter_id'] == '999'
    assert invite['uses'] == 0

    os.remove(db_path)


@pytest.mark.asyncio
async def test_record_invite_use():
    """Test recording when someone uses an invite."""
    db_path = "/tmp/test_invites3.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = InvitesDatabase(db_path)
    await db.initialize()

    await db.save_invite(guild_id=111, code="abc123", inviter_id="999", uses=0)
    await db.record_use(guild_id=111, code="abc123", joiner_id="888")

    invite = await db.get_invite(guild_id=111, code="abc123")
    assert invite['uses'] == 1

    uses = await db.get_uses_by_invite(guild_id=111, code="abc123")
    assert len(uses) == 1
    assert uses[0]['joiner_id'] == '888'

    os.remove(db_path)
