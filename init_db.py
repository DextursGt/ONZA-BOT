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
        print(f"🔧 Initializing database: {DATABASE_PATH}")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            print("✅ Foreign keys enabled")
            
            # Execute all migrations
            for i, migration in enumerate(MIGRATIONS):
                print(f"🔧 Executing migration {i+1}/{len(MIGRATIONS)}")
                await db.executescript(migration)
            
            await db.commit()
            print("✅ All migrations committed")
            
            # Verify tables were created
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                tables = await cursor.fetchall()
                table_names = [table[0] for table in tables]
                print(f"📋 Tables created: {table_names}")
            
            print(f"✅ Database initialized successfully: {DATABASE_PATH}")
            return True
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_bot_database())
