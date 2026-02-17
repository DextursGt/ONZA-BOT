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
