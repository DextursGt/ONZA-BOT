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
