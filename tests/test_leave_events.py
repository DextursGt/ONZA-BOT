"""Tests for leave events handler."""
import pytest
import os
from unittest.mock import AsyncMock, Mock
from events.cogs.leave_events import LeaveEventsHandler


@pytest.mark.asyncio
async def test_on_member_remove_sends_message():
    """Test leave event sends message when enabled."""
    bot = Mock()
    channel = AsyncMock()
    channel.send = AsyncMock()
    bot.get_channel = Mock(return_value=channel)

    member = Mock()
    member.guild.id = 1408125343071736009
    member.guild.name = "Test Server"
    member.guild.member_count = 99
    member.mention = "<@123>"
    member.name = "TestUser"
    member.__str__ = Mock(return_value="TestUser#1234")

    handler = LeaveEventsHandler(bot, db_path="/tmp/test_leave.db")
    await handler.db.initialize()

    await handler.db.save_leave_config({
        'guild_id': 1408125343071736009,
        'enabled': True,
        'channel_id': '1414836305300557887',
        'message_template': '¡Adiós %member_name%! Ahora somos %member_count%.'
    })

    await handler.on_member_remove(member)

    channel.send.assert_called_once()
    call_args = channel.send.call_args[0][0]
    assert 'TestUser' in call_args
    assert '99' in call_args

    os.remove("/tmp/test_leave.db")


@pytest.mark.asyncio
async def test_on_member_remove_disabled_does_nothing():
    """Test leave event does nothing when disabled."""
    bot = Mock()
    channel = AsyncMock()
    bot.get_channel = Mock(return_value=channel)

    member = Mock()
    member.guild.id = 1408125343071736009

    handler = LeaveEventsHandler(bot, db_path="/tmp/test_leave2.db")
    await handler.db.initialize()

    await handler.db.save_leave_config({
        'guild_id': 1408125343071736009,
        'enabled': False,
        'channel_id': '1414836305300557887',
        'message_template': 'Adiós'
    })

    await handler.on_member_remove(member)

    channel.send.assert_not_called()

    os.remove("/tmp/test_leave2.db")


@pytest.mark.asyncio
async def test_save_and_get_leave_config():
    """Test save and retrieve leave config from DB."""
    from events.databases.guilds_db import GuildsDatabase
    db = GuildsDatabase("/tmp/test_leave_cfg.db")
    await db.initialize()

    await db.save_leave_config({
        'guild_id': 111,
        'enabled': True,
        'channel_id': '999',
        'message_template': 'Bye %member_name%!'
    })

    config = await db.get_leave_config(111)
    assert config is not None
    assert config['channel_id'] == '999'
    assert config['message_template'] == 'Bye %member_name%!'

    os.remove("/tmp/test_leave_cfg.db")
