"""Tests for auto roles handler."""
import pytest
import os
from unittest.mock import AsyncMock, Mock
from events.cogs.auto_roles import AutoRolesHandler

@pytest.mark.asyncio
async def test_assign_auto_roles():
    """Test auto roles are assigned on join."""
    db_path = "/tmp/test_autoroles.db"

    # Clean up if exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Mock bot and role
    bot = Mock()
    role1 = Mock()
    role1.id = 111111111
    role2 = Mock()
    role2.id = 222222222

    # Mock member
    member = AsyncMock()
    member.guild.id = 1408125343071736009
    member.guild.get_role = Mock(side_effect=lambda rid: role1 if rid == 111111111 else role2)
    member.add_roles = AsyncMock()

    # Create handler
    handler = AutoRolesHandler(bot, db_path=db_path)
    await handler.db.initialize()

    # Add auto-roles config
    await handler.db.add_auto_role(1408125343071736009, '111111111', 0)
    await handler.db.add_auto_role(1408125343071736009, '222222222', 0)

    # Trigger event
    await handler.on_member_join(member)

    # Verify roles assigned
    assert member.add_roles.call_count == 2

    # Clean up
    os.remove(db_path)
