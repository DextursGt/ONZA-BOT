"""Tests for join events handler."""
import pytest
from unittest.mock import AsyncMock, Mock
from events.cogs.join_events import JoinEventsHandler

@pytest.mark.asyncio
async def test_on_member_join_sends_message():
    """Test join event sends message when enabled."""
    # Mock bot
    bot = Mock()
    channel = AsyncMock()
    channel.send = AsyncMock()
    bot.get_channel = Mock(return_value=channel)

    # Mock member
    member = Mock()
    member.guild.id = 1408125343071736009
    member.mention = "<@123>"
    member.name = "TestUser"
    member.guild.name = "Test Server"
    member.guild.member_count = 100

    # Create handler
    handler = JoinEventsHandler(bot, db_path="/tmp/test_join.db")
    await handler.db.initialize()

    # Save config
    await handler.db.save_join_config({
        'guild_id': 1408125343071736009,
        'enabled': True,
        'channel_id': '1414836305300557887',
        'message_template': '¡Bienvenido %member_mention%!',
        'embed_enabled': False
    })

    # Trigger event
    await handler.on_member_join(member)

    # Verify message sent
    channel.send.assert_called_once()
    call_args = channel.send.call_args[0][0]
    assert '¡Bienvenido <@123>!' in call_args

@pytest.mark.asyncio
async def test_on_member_join_disabled_does_nothing():
    """Test join event does nothing when disabled."""
    bot = Mock()
    channel = AsyncMock()
    bot.get_channel = Mock(return_value=channel)

    member = Mock()
    member.guild.id = 1408125343071736009

    handler = JoinEventsHandler(bot, db_path="/tmp/test_join2.db")
    await handler.db.initialize()

    # Save config with enabled=False
    await handler.db.save_join_config({
        'guild_id': 1408125343071736009,
        'enabled': False,
        'channel_id': '1414836305300557887',
        'message_template': 'Test'
    })

    await handler.on_member_join(member)

    # Verify no message sent
    channel.send.assert_not_called()
