# Events System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive events system with Join/Leave Messages, Auto Roles, Invite Tracking, Loyalty Points, Verification, and Dashboard UI.

**Architecture:** Event-driven bot cogs writing to 3 SQLite databases (guilds.db, invites.db, loyalty.db) with FastAPI dashboard for configuration. Template-based messages with 12 placeholders. No caching - fresh DB reads on each event.

**Tech Stack:** Python 3.11+, nextcord 2.x, FastAPI, aiosqlite, Bootstrap 5, vanilla JS

---

## Phase 1: Foundation (Databases + Join Messages + Auto Roles)

### Task 1: Install Dependencies

**Files:**
- Modify: `/root/ONZA-BOT/requirements.txt`

**Step 1: Add aiosqlite dependency**

Add to requirements.txt:
```
aiosqlite==0.19.0
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: "Successfully installed aiosqlite-0.19.0"

**Step 3: Verify installation**

Run: `python3 -c "import aiosqlite; print(aiosqlite.__version__)"`
Expected: "0.19.0"

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add aiosqlite dependency for events system"
```

---

### Task 2: Database Schema - guilds.db

**Files:**
- Create: `/root/ONZA-BOT/events/__init__.py`
- Create: `/root/ONZA-BOT/events/databases/__init__.py`
- Create: `/root/ONZA-BOT/events/databases/guilds_db.py`
- Create: `/root/ONZA-BOT/tests/test_guilds_db.py`

**Step 1: Write test for database initialization**

Create `/root/ONZA-BOT/tests/test_guilds_db.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_guilds_db.py::test_database_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'events'"

**Step 3: Create empty __init__.py files**

```bash
mkdir -p /root/ONZA-BOT/events/databases
touch /root/ONZA-BOT/events/__init__.py
touch /root/ONZA-BOT/events/databases/__init__.py
```

**Step 4: Implement GuildsDatabase class**

Create `/root/ONZA-BOT/events/databases/guilds_db.py`:
```python
"""Database for guild event configuration."""
import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GuildsDatabase:
    """Manage guild configuration database."""

    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "guilds.db"
        self.db_path = str(db_path)

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Join message configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS join_config (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    channel_id TEXT,
                    message_template TEXT,
                    embed_enabled BOOLEAN DEFAULT 0,
                    embed_title TEXT,
                    embed_description TEXT,
                    embed_color INTEGER,
                    embed_image_url TEXT
                )
            """)

            # Leave message configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS leave_config (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    channel_id TEXT,
                    message_template TEXT
                )
            """)

            # Join DM configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS join_dm_config (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    message_template TEXT
                )
            """)

            # Auto roles configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS auto_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    role_id TEXT,
                    delay_seconds INTEGER DEFAULT 0
                )
            """)

            # Verification configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS verification_config (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 0,
                    verification_channel_id TEXT,
                    verified_role_id TEXT,
                    unverified_role_id TEXT,
                    verification_message TEXT,
                    timeout_minutes INTEGER DEFAULT 10,
                    welcome_after_verify TEXT
                )
            """)

            await db.commit()
            logger.info(f"Guilds database initialized at {self.db_path}")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_guilds_db.py::test_database_initialization -v`
Expected: PASS (1 passed)

**Step 6: Commit**

```bash
git add events/ tests/test_guilds_db.py
git commit -m "feat: add guilds database with schema

- Create join_config, leave_config, join_dm_config tables
- Create auto_roles, verification_config tables
- Add initialization logic with tests"
```

---

### Task 3: Database Methods - Join Config

**Files:**
- Modify: `/root/ONZA-BOT/events/databases/guilds_db.py`
- Modify: `/root/ONZA-BOT/tests/test_guilds_db.py`

**Step 1: Write test for saving join config**

Add to `/root/ONZA-BOT/tests/test_guilds_db.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_guilds_db.py::test_save_and_get_join_config -v`
Expected: FAIL with "AttributeError: 'GuildsDatabase' object has no attribute 'save_join_config'"

**Step 3: Implement save_join_config method**

Add to `/root/ONZA-BOT/events/databases/guilds_db.py`:
```python
    async def save_join_config(self, config: dict):
        """Save or update join configuration for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO join_config
                (guild_id, enabled, channel_id, message_template, embed_enabled,
                 embed_title, embed_description, embed_color, embed_image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config['guild_id'],
                config.get('enabled', False),
                config.get('channel_id'),
                config.get('message_template'),
                config.get('embed_enabled', False),
                config.get('embed_title'),
                config.get('embed_description'),
                config.get('embed_color'),
                config.get('embed_image_url')
            ))
            await db.commit()
            logger.info(f"Saved join config for guild {config['guild_id']}")
```

**Step 4: Implement get_join_config method**

Add to `/root/ONZA-BOT/events/databases/guilds_db.py`:
```python
    async def get_join_config(self, guild_id: int) -> dict:
        """Get join configuration for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM join_config WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_guilds_db.py::test_save_and_get_join_config -v`
Expected: PASS (1 passed)

**Step 6: Commit**

```bash
git add events/databases/guilds_db.py tests/test_guilds_db.py
git commit -m "feat: add join config save/get methods with tests"
```

---

### Task 4: Template Engine

**Files:**
- Create: `/root/ONZA-BOT/events/template.py`
- Create: `/root/ONZA-BOT/tests/test_template.py`

**Step 1: Write test for template rendering**

Create `/root/ONZA-BOT/tests/test_template.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_template.py::test_render_member_placeholders -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'events.template'"

**Step 3: Implement Template class**

Create `/root/ONZA-BOT/events/template.py`:
```python
"""Message template engine with placeholder support."""
import logging

logger = logging.getLogger(__name__)

class Template:
    """Render message templates with placeholders."""

    PLACEHOLDERS = {
        '%member_mention%': lambda ctx: ctx['member'].mention,
        '%member_name%': lambda ctx: ctx['member'].name,
        '%member_tag%': lambda ctx: str(ctx['member']),
        '%member_id%': lambda ctx: ctx['member'].id,
        '%guild_name%': lambda ctx: ctx['guild'].name,
        '%member_count%': lambda ctx: ctx['guild'].member_count,
        '%inviter%': lambda ctx: ctx.get('inviter', {}).get('name', 'Unknown'),
        '%inviter_mention%': lambda ctx: ctx.get('inviter', {}).get('mention', '@Unknown'),
        '%invite_count%': lambda ctx: ctx.get('invite_count', 0),
        '%server_rules%': lambda ctx: ctx.get('rules', 'Ver #reglas'),
        '%verification_emoji%': lambda ctx: '✅',
        '%member_avatar%': lambda ctx: ctx['member'].display_avatar.url if hasattr(ctx['member'], 'display_avatar') else '[N/A]'
    }

    def render(self, template: str, context: dict) -> str:
        """Render template with context data.

        Args:
            template: Template string with placeholders
            context: Dictionary with data (member, guild, etc.)

        Returns:
            Rendered message string
        """
        if not template:
            return ""

        result = template

        for placeholder, func in self.PLACEHOLDERS.items():
            try:
                value = func(context)
                result = result.replace(placeholder, str(value))
            except KeyError:
                result = result.replace(placeholder, "[N/A]")
                logger.debug(f"Missing context for {placeholder}")
            except AttributeError as e:
                result = result.replace(placeholder, "[Error]")
                logger.warning(f"Attribute error for {placeholder}: {e}")
            except Exception as e:
                result = result.replace(placeholder, "[Error]")
                logger.error(f"Unexpected error for {placeholder}: {e}")

        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_template.py::test_render_member_placeholders -v`
Expected: PASS (1 passed)

**Step 5: Write test for error handling**

Add to `/root/ONZA-BOT/tests/test_template.py`:
```python
def test_render_with_missing_context():
    """Test rendering handles missing context gracefully."""
    template = Template()

    context = {}  # Empty context
    message = "Hello %member_mention%!"
    result = template.render(message, context)

    assert result == "Hello [N/A]!"
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_template.py::test_render_with_missing_context -v`
Expected: PASS (1 passed)

**Step 7: Commit**

```bash
git add events/template.py tests/test_template.py
git commit -m "feat: add template engine with 12 placeholders

- Support member, guild, inviter placeholders
- Safe error handling with fallbacks
- Tests for normal and error cases"
```

---

### Task 5: JoinEventsHandler Cog

**Files:**
- Create: `/root/ONZA-BOT/events/cogs/__init__.py`
- Create: `/root/ONZA-BOT/events/cogs/join_events.py`
- Create: `/root/ONZA-BOT/tests/test_join_events.py`

**Step 1: Write test for join event handler**

Create `/root/ONZA-BOT/tests/test_join_events.py`:
```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_join_events.py::test_on_member_join_sends_message -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'events.cogs'"

**Step 3: Create cogs directory**

```bash
mkdir -p /root/ONZA-BOT/events/cogs
touch /root/ONZA-BOT/events/cogs/__init__.py
```

**Step 4: Implement JoinEventsHandler**

Create `/root/ONZA-BOT/events/cogs/join_events.py`:
```python
"""Join events handler cog."""
import nextcord
from nextcord.ext import commands
import logging
from events.databases.guilds_db import GuildsDatabase
from events.template import Template

logger = logging.getLogger(__name__)

class JoinEventsHandler(commands.Cog):
    """Handle member join events."""

    def __init__(self, bot, db_path=None):
        """Initialize join events handler.

        Args:
            bot: Discord bot instance
            db_path: Optional path to database (for testing)
        """
        self.bot = bot
        self.db = GuildsDatabase(db_path)
        self.template = Template()

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        """Triggered when user joins guild.

        Args:
            member: Member who joined
        """
        guild_id = member.guild.id

        try:
            # Load config from DB
            config = await self.db.get_join_config(guild_id)

            if not config or not config['enabled']:
                logger.debug(f"Join messages disabled for guild {guild_id}")
                return

            # Build context
            context = {
                'member': member,
                'guild': member.guild,
                'member_count': member.guild.member_count
            }

            # Render template
            message = self.template.render(config['message_template'], context)

            # Get channel
            channel = self.bot.get_channel(int(config['channel_id']))
            if not channel:
                logger.error(f"Channel {config['channel_id']} not found for join message")
                return

            # Send message
            if config['embed_enabled']:
                embed = nextcord.Embed(
                    title=config.get('embed_title', ''),
                    description=message,
                    color=config.get('embed_color', 0x00E5A8)
                )
                if config.get('embed_image_url'):
                    embed.set_image(url=config['embed_image_url'])
                await channel.send(embed=embed)
                logger.info(f"Join embed sent for {member.id} in guild {guild_id}")
            else:
                await channel.send(message)
                logger.info(f"Join message sent for {member.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in on_member_join for {member.id}: {e}", exc_info=True)

def setup(bot):
    """Load the cog."""
    bot.add_cog(JoinEventsHandler(bot))
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_join_events.py::test_on_member_join_sends_message -v`
Expected: PASS (1 passed)

**Step 6: Test disabled state**

Add to `/root/ONZA-BOT/tests/test_join_events.py`:
```python
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
```

**Step 7: Run test to verify it passes**

Run: `pytest tests/test_join_events.py::test_on_member_join_disabled_does_nothing -v`
Expected: PASS (1 passed)

**Step 8: Commit**

```bash
git add events/cogs/ tests/test_join_events.py
git commit -m "feat: add JoinEventsHandler cog

- Listen to on_member_join events
- Load config from guilds.db
- Render template and send to channel
- Support both text and embed messages
- Tests for enabled and disabled states"
```

---

### Task 6: AutoRolesHandler Cog

**Files:**
- Create: `/root/ONZA-BOT/events/cogs/auto_roles.py`
- Modify: `/root/ONZA-BOT/events/databases/guilds_db.py`
- Create: `/root/ONZA-BOT/tests/test_auto_roles.py`

**Step 1: Add auto roles DB methods to GuildsDatabase**

Add to `/root/ONZA-BOT/events/databases/guilds_db.py`:
```python
    async def get_auto_roles(self, guild_id: int) -> list:
        """Get all auto-roles for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM auto_roles WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def add_auto_role(self, guild_id: int, role_id: str, delay_seconds: int = 0):
        """Add an auto-role configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO auto_roles (guild_id, role_id, delay_seconds) VALUES (?, ?, ?)",
                (guild_id, role_id, delay_seconds)
            )
            await db.commit()
            logger.info(f"Added auto-role {role_id} for guild {guild_id}")

    async def remove_auto_role(self, role_config_id: int):
        """Remove an auto-role configuration."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM auto_roles WHERE id = ?",
                (role_config_id,)
            )
            await db.commit()
            logger.info(f"Removed auto-role config {role_config_id}")
```

**Step 2: Write test for AutoRolesHandler**

Create `/root/ONZA-BOT/tests/test_auto_roles.py`:
```python
"""Tests for auto roles handler."""
import pytest
from unittest.mock import AsyncMock, Mock
from events.cogs.auto_roles import AutoRolesHandler

@pytest.mark.asyncio
async def test_assign_auto_roles():
    """Test auto roles are assigned on join."""
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
    handler = AutoRolesHandler(bot, db_path="/tmp/test_autoroles.db")
    await handler.db.initialize()

    # Add auto-roles config
    await handler.db.add_auto_role(1408125343071736009, '111111111', 0)
    await handler.db.add_auto_role(1408125343071736009, '222222222', 0)

    # Trigger event
    await handler.on_member_join(member)

    # Verify roles assigned
    assert member.add_roles.call_count == 2
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_auto_roles.py::test_assign_auto_roles -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'events.cogs.auto_roles'"

**Step 4: Implement AutoRolesHandler**

Create `/root/ONZA-BOT/events/cogs/auto_roles.py`:
```python
"""Auto roles handler cog."""
import nextcord
from nextcord.ext import commands
import asyncio
import logging
from events.databases.guilds_db import GuildsDatabase

logger = logging.getLogger(__name__)

class AutoRolesHandler(commands.Cog):
    """Auto-assign roles on member join."""

    def __init__(self, bot, db_path=None):
        """Initialize auto roles handler.

        Args:
            bot: Discord bot instance
            db_path: Optional path to database (for testing)
        """
        self.bot = bot
        self.db = GuildsDatabase(db_path)

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        """Assign configured auto-roles when user joins.

        Args:
            member: Member who joined
        """
        guild_id = member.guild.id

        try:
            # Get auto-roles config
            roles_config = await self.db.get_auto_roles(guild_id)

            if not roles_config:
                logger.debug(f"No auto-roles configured for guild {guild_id}")
                return

            # Assign each role
            for role_config in roles_config:
                role = member.guild.get_role(int(role_config['role_id']))

                if not role:
                    logger.warning(f"Role {role_config['role_id']} not found in guild {guild_id}")
                    continue

                # Delay if configured
                if role_config['delay_seconds'] > 0:
                    await asyncio.sleep(role_config['delay_seconds'])

                # Assign role
                await member.add_roles(role, reason="Auto-role assignment")
                logger.info(f"Assigned role {role.name} to {member.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error assigning auto-roles to {member.id}: {e}", exc_info=True)

def setup(bot):
    """Load the cog."""
    bot.add_cog(AutoRolesHandler(bot))
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_auto_roles.py::test_assign_auto_roles -v`
Expected: PASS (1 passed)

**Step 6: Commit**

```bash
git add events/cogs/auto_roles.py events/databases/guilds_db.py tests/test_auto_roles.py
git commit -m "feat: add AutoRolesHandler cog

- Assign roles automatically on join
- Support delay before assignment
- DB methods for add/remove/get auto-roles
- Tests for role assignment"
```

---

### Task 7: Load Cogs in main.py

**Files:**
- Modify: `/root/ONZA-BOT/main.py`

**Step 1: Initialize guilds database on bot start**

Add to `/root/ONZA-BOT/main.py` in the `IntegratedONZABot.__init__` method:
```python
        # Initialize events system databases
        from events.databases.guilds_db import GuildsDatabase
        self.guilds_db = GuildsDatabase()
```

Add to `IntegratedONZABot` setup method (after `await super().setup_hook()`):
```python
        # Initialize events databases
        await self.guilds_db.initialize()
        logger.info("Events databases initialized")
```

**Step 2: Load event cogs**

Add to `/root/ONZA-BOT/main.py` in setup method (after database init):
```python
        # Load event handler cogs
        self.load_extension('events.cogs.join_events')
        self.load_extension('events.cogs.auto_roles')
        logger.info("Event handler cogs loaded")
```

**Step 3: Test bot starts without errors**

Run: `python3 main.py`
Expected: Bot starts, logs show "Events databases initialized" and "Event handler cogs loaded"
Stop with Ctrl+C after verifying logs.

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: integrate events system into main bot

- Initialize guilds database on startup
- Load JoinEventsHandler and AutoRolesHandler cogs
- Create data/guilds.db on first run"
```

---

### Task 8: Dashboard API - Join Config Endpoints

**Files:**
- Create: `/root/ONZA-BOT/dashboard/api/__init__.py`
- Create: `/root/ONZA-BOT/dashboard/api/events.py`
- Modify: `/root/ONZA-BOT/dashboard/app.py`

**Step 1: Create events API module**

```bash
mkdir -p /root/ONZA-BOT/dashboard/api
touch /root/ONZA-BOT/dashboard/api/__init__.py
```

Create `/root/ONZA-BOT/dashboard/api/events.py`:
```python
"""Events configuration API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from dashboard.auth import authenticate_user
from dashboard.bot_api import bot_api

router = APIRouter(prefix="/api/events", tags=["events"])

class JoinConfigRequest(BaseModel):
    """Join message configuration."""
    guild_id: Union[int, str]
    enabled: bool
    channel_id: Union[int, str]
    message_template: str
    embed_enabled: bool = False
    embed_title: Optional[str] = None
    embed_description: Optional[str] = None
    embed_color: Optional[int] = None
    embed_image_url: Optional[str] = None

    @field_validator('guild_id', 'channel_id')
    @classmethod
    def convert_ids(cls, v):
        return int(v) if isinstance(v, str) else v

@router.get("/join/{guild_id}")
async def get_join_config(guild_id: int, username: str = Depends(authenticate_user)):
    """Get join message configuration for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    config = await bot_api.bot.guilds_db.get_join_config(guild_id)
    return config or {}

@router.post("/join/configure")
async def configure_join(request: JoinConfigRequest, username: str = Depends(authenticate_user)):
    """Configure join messages for a guild."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    # Validate channel exists
    channel = bot_api.bot.get_channel(int(request.channel_id))
    if not channel:
        raise HTTPException(400, "Canal no encontrado")

    # Validate bot has permissions
    perms = channel.permissions_for(channel.guild.me)
    if not perms.send_messages:
        raise HTTPException(400, "Bot no tiene permisos para enviar mensajes en ese canal")

    # Save config
    await bot_api.bot.guilds_db.save_join_config(request.dict())

    return {"success": True, "message": "Configuración guardada"}

@router.post("/join/toggle")
async def toggle_join(guild_id: int, enabled: bool, username: str = Depends(authenticate_user)):
    """Toggle join messages on/off."""
    if not bot_api.bot:
        raise HTTPException(503, "Bot not connected")

    # Get current config
    config = await bot_api.bot.guilds_db.get_join_config(guild_id)
    if not config:
        raise HTTPException(404, "No configuration found")

    # Update enabled status
    config['enabled'] = enabled
    await bot_api.bot.guilds_db.save_join_config(config)

    return {"success": True, "enabled": enabled}
```

**Step 2: Register events router in app.py**

Add to `/root/ONZA-BOT/dashboard/app.py` after existing imports:
```python
from dashboard.api.events import router as events_router
```

Add after app initialization (after `app = FastAPI(...)`):
```python
# Register API routers
app.include_router(events_router)
```

**Step 3: Test API endpoints**

Run: `curl http://193.43.134.31:8000/api/events/join/1408125343071736009`
Expected: Returns empty object `{}` or existing config

**Step 4: Commit**

```bash
git add dashboard/api/ dashboard/app.py
git commit -m "feat: add events API endpoints for join config

- GET /api/events/join/{guild_id}
- POST /api/events/join/configure
- POST /api/events/join/toggle
- Validation for channel and permissions"
```

---

### Task 9: Dashboard UI - Events Configuration Page

**Files:**
- Create: `/root/ONZA-BOT/dashboard/templates/events.html`
- Create: `/root/ONZA-BOT/dashboard/static/js/events.js`
- Modify: `/root/ONZA-BOT/dashboard/app.py`

**Step 1: Add events page route**

Add to `/root/ONZA-BOT/dashboard/app.py`:
```python
@app.get("/events", response_class=HTMLResponse)
async def events_page(request: Request, username: str = Depends(authenticate_user)):
    """Events configuration page."""
    return templates.TemplateResponse("events.html", {"request": request, "username": username})
```

**Step 2: Create events HTML template**

Create `/root/ONZA-BOT/dashboard/templates/events.html`:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Events - ONZA-BOT Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">ONZA-BOT Dashboard</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">Home</a>
                <a class="nav-link active" href="/events">Events</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <h1><i class="bi bi-calendar-event"></i> Events Configuration</h1>

        <!-- Alert container -->
        <div id="alert-container"></div>

        <!-- Join Messages Card -->
        <div class="card mt-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5><i class="bi bi-door-open"></i> Join Messages</h5>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" id="join-enabled">
                    <label class="form-check-label" for="join-enabled">Enabled</label>
                </div>
            </div>
            <div class="card-body">
                <form id="join-config-form">
                    <div class="mb-3">
                        <label for="join-channel" class="form-label">Channel</label>
                        <select class="form-select" id="join-channel" required>
                            <option value="">Select a channel</option>
                        </select>
                    </div>

                    <div class="mb-3">
                        <label for="join-message" class="form-label">Message Template</label>
                        <textarea class="form-control" id="join-message" rows="3"
                                  placeholder="¡Bienvenido %member_mention% a %guild_name%!"></textarea>
                        <small class="text-muted">
                            Available: %member_mention%, %member_name%, %guild_name%, %member_count%
                        </small>
                    </div>

                    <div class="form-check mb-3">
                        <input class="form-check-input" type="checkbox" id="join-embed">
                        <label class="form-check-label" for="join-embed">Use Embed</label>
                    </div>

                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save"></i> Save Configuration
                    </button>
                </form>
            </div>
        </div>

        <!-- Auto Roles Card -->
        <div class="card mt-4">
            <div class="card-header">
                <h5><i class="bi bi-person-badge"></i> Auto Roles</h5>
            </div>
            <div class="card-body">
                <p>Configure roles to automatically assign when users join.</p>
                <div id="auto-roles-list" class="list-group mb-3">
                    <!-- Auto roles will be loaded here -->
                </div>
                <button class="btn btn-success" id="add-auto-role-btn">
                    <i class="bi bi-plus-circle"></i> Add Auto Role
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/events.js"></script>
</body>
</html>
```

**Step 3: Create events JavaScript**

Create `/root/ONZA-BOT/dashboard/static/js/events.js`:
```javascript
/**
 * Events Configuration JavaScript
 */

let guildId = null;

// Initialize
document.addEventListener('DOMContentLoaded', async function() {
    // Get guild ID
    const configResponse = await fetch('/api/config');
    const config = await configResponse.json();
    guildId = config.guild_id;

    // Load channels
    await loadChannels();

    // Load join config
    await loadJoinConfig();

    // Setup form handlers
    setupFormHandlers();
});

/**
 * Load channels into select
 */
async function loadChannels() {
    try {
        const response = await fetch(`/api/channels/${guildId}`);
        const data = await response.json();

        const select = document.getElementById('join-channel');
        select.innerHTML = '<option value="">Select a channel</option>';

        data.channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.id;
            option.textContent = `# ${channel.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading channels:', error);
    }
}

/**
 * Load join configuration
 */
async function loadJoinConfig() {
    try {
        const response = await fetch(`/api/events/join/${guildId}`);
        const config = await response.json();

        if (config.guild_id) {
            document.getElementById('join-enabled').checked = config.enabled;
            document.getElementById('join-channel').value = config.channel_id;
            document.getElementById('join-message').value = config.message_template || '';
            document.getElementById('join-embed').checked = config.embed_enabled;
        }
    } catch (error) {
        console.error('Error loading join config:', error);
    }
}

/**
 * Setup form handlers
 */
function setupFormHandlers() {
    // Join config form
    document.getElementById('join-config-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            guild_id: guildId,
            enabled: document.getElementById('join-enabled').checked,
            channel_id: document.getElementById('join-channel').value,
            message_template: document.getElementById('join-message').value,
            embed_enabled: document.getElementById('join-embed').checked
        };

        try {
            const response = await fetch('/api/events/join/configure', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                showAlert('✅ Configuration saved successfully', 'success');
            } else {
                showAlert(`❌ Error: ${result.detail || 'Unknown error'}`, 'danger');
            }
        } catch (error) {
            showAlert('❌ Error saving configuration', 'danger');
            console.error(error);
        }
    });

    // Toggle enabled
    document.getElementById('join-enabled').addEventListener('change', async (e) => {
        try {
            const response = await fetch(`/api/events/join/toggle?guild_id=${guildId}&enabled=${e.target.checked}`, {
                method: 'POST'
            });

            if (response.ok) {
                showAlert(`Join messages ${e.target.checked ? 'enabled' : 'disabled'}`, 'info');
            }
        } catch (error) {
            console.error('Error toggling:', error);
        }
    });
}

/**
 * Show alert
 */
function showAlert(message, type) {
    const container = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    setTimeout(() => alert.remove(), 5000);
}
```

**Step 4: Test events page**

Navigate to: `http://193.43.134.31:8000/events`
Expected: Page loads, channels populate in dropdown

**Step 5: Commit**

```bash
git add dashboard/templates/events.html dashboard/static/js/events.js dashboard/app.py
git commit -m "feat: add events configuration UI

- Events page with join messages configuration
- Channel selector from API
- Toggle enable/disable
- Save configuration form
- Real-time config loading"
```

---

### Task 10: Test Phase 1 End-to-End

**Files:**
- None (testing only)

**Step 1: Configure join message via dashboard**

1. Navigate to `http://193.43.134.31:8000/events`
2. Enable join messages toggle
3. Select a channel
4. Enter template: `¡Bienvenido %member_mention% a %guild_name%! Somos %member_count% miembros.`
5. Click Save Configuration
6. Expected: Success alert

**Step 2: Verify config saved to database**

Run:
```bash
sqlite3 /root/ONZA-BOT/data/guilds.db "SELECT * FROM join_config WHERE guild_id = 1408125343071736009"
```
Expected: Row with enabled=1, your channel_id, and template

**Step 3: Test join event (if possible)**

If you have a test Discord server:
1. Create an invite link
2. Join with a test account
3. Expected: Welcome message appears in configured channel

**Step 4: Verify logs**

Run: `pm2 logs ONZA-BOT --lines 20`
Expected: See "Join message sent for [user_id] in guild [guild_id]"

**Step 5: Commit test documentation**

```bash
git add -A
git commit -m "test: Phase 1 complete - join messages and auto roles working

Verified:
- Database initialization
- Template rendering
- Join event handler
- Dashboard configuration
- End-to-end flow from UI to Discord"
```

---

## Phase 2: Invite Tracking + Loyalty System

*Phase 2 will continue with similar detailed, test-driven tasks for:*
- *Task 11: Database Schema - invites.db*
- *Task 12: Database Schema - loyalty.db*
- *Task 13: InviteTracker Cog*
- *Task 14: LoyaltySystem Class*
- *Task 15: Fraud Detection Logic*
- *Task 16: Dashboard API - Invite Stats*
- *Task 17: Dashboard UI - Invite Statistics*

## Phase 3: Leave Messages + Join DM

*Phase 3 will implement:*
- *Task 18: LeaveEventsHandler Cog*
- *Task 19: Join DM Functionality*
- *Task 20: Dashboard UI for Leave/DM Config*

## Phase 4: Verification System

*Phase 4 will implement:*
- *Task 21: VerificationHandler Cog*
- *Task 22: Timeout Mechanism*
- *Task 23: Dashboard Verification Config*

---

## Verification Commands

After each phase:

```bash
# Check all databases exist
ls -lh /root/ONZA-BOT/data/*.db

# View guilds.db schema
sqlite3 /root/ONZA-BOT/data/guilds.db ".schema"

# Run all tests
pytest tests/ -v

# Check bot logs
pm2 logs ONZA-BOT --lines 50

# Dashboard health
curl http://193.43.134.31:8000/health
```

## Success Criteria (Phase 1)

- ✅ guilds.db created with 5 tables
- ✅ Template engine renders 12 placeholders
- ✅ JoinEventsHandler sends messages on join
- ✅ AutoRolesHandler assigns roles on join
- ✅ Dashboard UI loads and saves join config
- ✅ All tests passing (pytest)
- ✅ Bot runs without crashes (pm2 logs clean)
