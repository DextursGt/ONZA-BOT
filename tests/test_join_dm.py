"""Tests for join DM functionality."""
import pytest
import os
from unittest.mock import AsyncMock, Mock
from events.cogs.join_events import JoinEventsHandler


@pytest.mark.asyncio
async def test_sends_dm_when_enabled():
    """Test DM is sent to new member when enabled."""
    bot = Mock()
    bot.get_channel = Mock(return_value=None)

    member = AsyncMock()
    member.guild.id = 1408125343071736009
    member.guild.name = "Test Server"
    member.guild.member_count = 100
    member.mention = "<@123>"
    member.name = "TestUser"
    member.__str__ = Mock(return_value="TestUser#1234")
    member.send = AsyncMock()

    handler = JoinEventsHandler(bot, db_path="/tmp/test_joindm.db")
    await handler.db.initialize()

    # DM enabled, channel join disabled
    await handler.db.save_join_dm_config({
        'guild_id': 1408125343071736009,
        'enabled': True,
        'message_template': '¡Bienvenido a %guild_name%, %member_name%!'
    })

    await handler.on_member_join(member)

    member.send.assert_called_once()
    dm_text = member.send.call_args[0][0]
    assert 'Test Server' in dm_text
    assert 'TestUser' in dm_text

    os.remove("/tmp/test_joindm.db")


@pytest.mark.asyncio
async def test_no_dm_when_disabled():
    """Test DM is not sent when disabled."""
    bot = Mock()
    bot.get_channel = Mock(return_value=None)

    member = AsyncMock()
    member.guild.id = 1408125343071736009
    member.send = AsyncMock()

    handler = JoinEventsHandler(bot, db_path="/tmp/test_joindm2.db")
    await handler.db.initialize()

    await handler.db.save_join_dm_config({
        'guild_id': 1408125343071736009,
        'enabled': False,
        'message_template': 'Bienvenido'
    })

    await handler.on_member_join(member)

    member.send.assert_not_called()

    os.remove("/tmp/test_joindm2.db")


@pytest.mark.asyncio
async def test_dm_failure_does_not_crash_join():
    """Test that a failed DM does not prevent the rest of join processing."""
    bot = Mock()
    bot.get_channel = Mock(return_value=None)

    member = AsyncMock()
    member.guild.id = 111
    member.guild.name = "Server"
    member.guild.member_count = 5
    member.mention = "<@1>"
    member.name = "User"
    member.__str__ = Mock(return_value="User#0001")
    member.send = AsyncMock(side_effect=Exception("Cannot send DM"))

    handler = JoinEventsHandler(bot, db_path="/tmp/test_joindm3.db")
    await handler.db.initialize()

    await handler.db.save_join_dm_config({
        'guild_id': 111,
        'enabled': True,
        'message_template': 'Hola %member_name%'
    })

    # Should not raise
    await handler.on_member_join(member)

    os.remove("/tmp/test_joindm3.db")
