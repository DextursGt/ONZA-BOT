"""Database for invite tracking."""
import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class InvitesDatabase:
    """Manage invite tracking database."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "invites.db"
        self.db_path = str(db_path)

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invite_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    inviter_id TEXT NOT NULL,
                    uses INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, code)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invite_uses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    joiner_id TEXT NOT NULL,
                    is_fraud BOOLEAN DEFAULT 0,
                    fraud_reason TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Invites database initialized at {self.db_path}")

    async def save_invite(self, guild_id: int, code: str, inviter_id: str, uses: int = 0):
        """Save or update an invite code."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invite_codes (guild_id, code, inviter_id, uses)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, code) DO UPDATE SET uses=excluded.uses
            """, (guild_id, code, inviter_id, uses))
            await db.commit()

    async def get_invite(self, guild_id: int, code: str) -> dict:
        """Get invite by guild and code."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM invite_codes WHERE guild_id=? AND code=?",
                (guild_id, code)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_invites(self, guild_id: int) -> list:
        """Get all invites for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM invite_codes WHERE guild_id=?", (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def record_use(self, guild_id: int, code: str, joiner_id: str,
                         is_fraud: bool = False, fraud_reason: str = None):
        """Record that someone used an invite."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invite_uses (guild_id, code, joiner_id, is_fraud, fraud_reason)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, code, joiner_id, is_fraud, fraud_reason))
            if not is_fraud:
                await db.execute("""
                    UPDATE invite_codes SET uses = uses + 1
                    WHERE guild_id=? AND code=?
                """, (guild_id, code))
            await db.commit()

    async def get_uses_by_invite(self, guild_id: int, code: str) -> list:
        """Get all uses of a specific invite."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM invite_uses WHERE guild_id=? AND code=? AND is_fraud=0",
                (guild_id, code)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_inviter_stats(self, guild_id: int, inviter_id: str) -> dict:
        """Get stats for a specific inviter."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COALESCE(SUM(uses), 0) as total_uses
                FROM invite_codes WHERE guild_id=? AND inviter_id=?
            """, (guild_id, inviter_id)) as cursor:
                row = await cursor.fetchone()
                return {'total_uses': row[0] if row else 0, 'inviter_id': inviter_id}
