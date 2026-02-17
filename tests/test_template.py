"""Tests for template engine."""
import pytest
from events.template import Template

def test_render_member_placeholders():
    """Test rendering member-related placeholders."""
    template = Template()

    # Mock member object
    class MockMember:
        mention = "<@123456789>"
        name = "TestUser"
        id = 123456789

        def __str__(self):
            return "TestUser#1234"

    class MockGuild:
        name = "Test Server"
        member_count = 100

    context = {
        'member': MockMember(),
        'guild': MockGuild()
    }

    message = "¡Bienvenido %member_mention% a %guild_name%! Somos %member_count% miembros."
    result = template.render(message, context)

    assert result == "¡Bienvenido <@123456789> a Test Server! Somos 100 miembros."

def test_render_with_missing_context():
    """Test rendering handles missing context gracefully."""
    template = Template()

    context = {}  # Empty context
    message = "Hello %member_mention%!"
    result = template.render(message, context)

    assert result == "Hello [N/A]!"
