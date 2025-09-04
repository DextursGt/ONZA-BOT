"""
Database initialization for ONZA Bot
Creates all necessary tables for the bot to function
"""
import aiosqlite
import os
from config import DATABASE_PATH, MIGRATIONS

async def init_bot_database():
    """Initialize the bot database with all necessary tables"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Execute all migrations
            for migration in MIGRATIONS:
                await db.executescript(migration)
            
            await db.commit()
            
            print(f"✅ Database initialized successfully: {DATABASE_PATH}")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_bot_database())
