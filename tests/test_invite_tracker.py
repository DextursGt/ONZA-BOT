"""Tests for invite tracker cog."""
import pytest
import os
from unittest.mock import AsyncMock, Mock, patch
from events.cogs.invite_tracker import InviteTracker


def make_mock_invite(code, inviter_id, uses):
    inv = Mock()
    inv.code = code
    inv.inviter = Mock()
    inv.inviter.id = inviter_id
    inv.uses = uses
    return inv


@pytest.mark.asyncio
async def test_detect_used_invite():
    """Test tracker detects which invite was used."""
    bot = Mock()
    bot.guilds = []

    tracker = InviteTracker(bot, db_path="/tmp/test_tracker.db")
    await tracker.db.initialize()

    guild = Mock()
    guild.id = 111

    # Simulate cached invites (before join)
    before = {
        'abc': make_mock_invite('abc', 777, 5),
        'xyz': make_mock_invite('xyz', 888, 3),
    }
    # After join: 'abc' went from 5 to 6
    after = [
        make_mock_invite('abc', 777, 6),
        make_mock_invite('xyz', 888, 3),
    ]

    tracker.invite_cache[111] = before

    used = tracker._find_used_invite(before, after)
    assert used is not None
    assert used.code == 'abc'
    assert used.inviter.id == 777

    # Cleanup
    os.remove("/tmp/test_tracker.db")


@pytest.mark.asyncio
async def test_no_invite_found_returns_none():
    """Test returns None when no invite change detected."""
    bot = Mock()
    tracker = InviteTracker(bot, db_path="/tmp/test_tracker2.db")
    await tracker.db.initialize()

    before = {'abc': make_mock_invite('abc', 777, 5)}
    after = [make_mock_invite('abc', 777, 5)]  # No change

    used = tracker._find_used_invite(before, after)
    assert used is None

    os.remove("/tmp/test_tracker2.db")
