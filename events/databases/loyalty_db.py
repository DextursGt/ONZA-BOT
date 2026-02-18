"""Database for loyalty points system."""
import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LoyaltyDatabase:
    """Manage loyalty points database."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "loyalty.db"
        self.db_path = str(db_path)

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS loyalty_points (
                    guild_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    total_points INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS loyalty_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Loyalty database initialized at {self.db_path}")

    async def add_points(self, guild_id: int, user_id: str, points: int, reason: str = None):
        """Add points to a user and record in history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO loyalty_points (guild_id, user_id, total_points)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    total_points = total_points + excluded.total_points
            """, (guild_id, user_id, points))
            await db.execute("""
                INSERT INTO loyalty_history (guild_id, user_id, points, reason)
                VALUES (?, ?, ?, ?)
            """, (guild_id, user_id, points, reason))
            await db.commit()
            logger.info(f"Added {points} points to user {user_id} in guild {guild_id}")

    async def get_points(self, guild_id: int, user_id: str) -> int:
        """Get total points for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT total_points FROM loyalty_points WHERE guild_id=? AND user_id=?",
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        """Get top users by points."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT user_id, total_points
                FROM loyalty_points
                WHERE guild_id=?
                ORDER BY total_points DESC
                LIMIT ?
            """, (guild_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_history(self, guild_id: int, user_id: str, limit: int = 20) -> list:
        """Get points history for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT points, reason, created_at
                FROM loyalty_history
                WHERE guild_id=? AND user_id=?
                ORDER BY created_at DESC LIMIT ?
            """, (guild_id, user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
