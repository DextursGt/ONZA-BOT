"""
Store database module for ONZA bot
Manages products and product options with variants support
"""
import os
import aiosqlite
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime

# Database path from environment or default
STORE_DATABASE_PATH = os.getenv("STORE_DATABASE_PATH", "onza_store.db")

# Schema definitions
SCHEMA = """
-- Products table
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    notes TEXT,
    image_url TEXT,
    active INTEGER DEFAULT 1,
    sort INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Product options/variants table
CREATE TABLE IF NOT EXISTS product_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    label TEXT NOT NULL,
    price_mxn REAL NOT NULL CHECK(price_mxn > 0),
    duration_days INTEGER NOT NULL,
    emoji TEXT DEFAULT '🪙',
    active INTEGER DEFAULT 1,
    sort INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (sku) REFERENCES products(sku) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);
CREATE INDEX IF NOT EXISTS idx_products_sort ON products(sort);
CREATE INDEX IF NOT EXISTS idx_product_options_sku ON product_options(sku);
CREATE INDEX IF NOT EXISTS idx_product_options_active ON product_options(active);
CREATE INDEX IF NOT EXISTS idx_product_options_sort ON product_options(sort, price_mxn);
"""


async def ensure_store_db():
    """Initialize store database with schema and indexes"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Execute schema
        await db.executescript(SCHEMA)
        await db.commit()


async def upsert_product(sku: str, name: str, image_url: Optional[str] = None, 
                        notes: Optional[str] = None, sort: int = 0, active: int = 1) -> bool:
    """Insert or update a product"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Check if exists
        async with db.execute("SELECT sku FROM products WHERE sku = ?", (sku,)) as cursor:
            exists = await cursor.fetchone() is not None
        
        now = datetime.utcnow().isoformat()
        
        if exists:
            await db.execute("""
                UPDATE products 
                SET name = ?, image_url = ?, notes = ?, sort = ?, active = ?, updated_at = ?
                WHERE sku = ?
            """, (name, image_url, notes, sort, active, now, sku))
        else:
            await db.execute("""
                INSERT INTO products (sku, name, image_url, notes, sort, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, image_url, notes, sort, active, now))
        
        await db.commit()
        return True


async def soft_delete_product(sku: str) -> bool:
    """Soft delete a product by setting active = 0"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        
        cursor = await db.execute("UPDATE products SET active = 0 WHERE sku = ?", (sku,))
        await db.commit()
        
        return cursor.rowcount > 0


async def get_product(sku: str) -> Optional[Dict[str, Any]]:
    """Get a single product by SKU"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        
        async with db.execute("SELECT * FROM products WHERE sku = ?", (sku,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def list_products(include_inactive: bool = False) -> List[Dict[str, Any]]:
    """List all products ordered by sort ASC, name ASC"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM products"
        if not include_inactive:
            query += " WHERE active = 1"
        query += " ORDER BY sort ASC, name ASC"
        
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_option(sku: str, label: str, price_mxn: float, duration_days: int,
                    emoji: str = "🪙", sort: int = 0, active: int = 1) -> Optional[int]:
    """Add a new product option, returns the created ID"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Verify product exists
        async with db.execute("SELECT sku FROM products WHERE sku = ?", (sku,)) as cursor:
            if not await cursor.fetchone():
                return None
        
        cursor = await db.execute("""
            INSERT INTO product_options (sku, label, price_mxn, duration_days, emoji, sort, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sku, label, price_mxn, duration_days, emoji, sort, active))
        
        await db.commit()
        return cursor.lastrowid


async def delete_option(option_id: int) -> bool:
    """Delete a product option by ID"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        
        cursor = await db.execute("DELETE FROM product_options WHERE id = ?", (option_id,))
        await db.commit()
        
        return cursor.rowcount > 0


async def list_options(sku: str, active_only: bool = True) -> List[Dict[str, Any]]:
    """List options for a product ordered by sort ASC, price_mxn ASC"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM product_options WHERE sku = ?"
        params = [sku]
        
        if active_only:
            query += " AND active = 1"
        
        query += " ORDER BY sort ASC, price_mxn ASC"
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def cheapest_options_by_sku() -> List[Tuple[str, str, Dict[str, Any]]]:
    """Get the cheapest option for each active product"""
    async with aiosqlite.connect(STORE_DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row
        
        query = """
        SELECT p.sku, p.name, o.*
        FROM products p
        INNER JOIN (
            SELECT sku, MIN(price_mxn) as min_price
            FROM product_options
            WHERE active = 1
            GROUP BY sku
        ) cheapest ON p.sku = cheapest.sku
        INNER JOIN product_options o ON o.sku = p.sku AND o.price_mxn = cheapest.min_price AND o.active = 1
        WHERE p.active = 1
        ORDER BY p.sort ASC, p.name ASC
        """
        
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                sku = row_dict['sku']
                name = row_dict['name']
                # Remove sku and name from option dict
                option = {k: v for k, v in row_dict.items() if k not in ['sku', 'name']}
                result.append((sku, name, option))
            return result


async def sync_legacy_products_into_store(legacy_rows: List[Tuple]) -> int:
    """
    Sync legacy products into the store database
    legacy_rows: List of tuples (id, sku, name, description, price_cents, currency, duration_days, ...)
    Returns number of products synced
    """
    synced = 0
    
    for row in legacy_rows:
        # Extract fields - adjust indices based on actual legacy schema
        if len(row) < 7:
            continue
            
        sku = row[1]
        name = row[2]
        description = row[3]
        price_cents = row[4]
        currency = row[5]
        duration_days = row[6] or 30
        
        # Check if already exists in store
        existing = await get_product(sku)
        if existing:
            # Check if has options
            options = await list_options(sku, active_only=False)
            if options:
                continue  # Already has options, skip
        
        # Create or update product
        await upsert_product(sku, name, notes=description)
        
        # Calculate price in MXN
        if currency == "MXN":
            price_mxn = price_cents / 100.0
        else:
            # Simple conversion fallback
            price_mxn = round(price_cents / 100.0)
        
        # Determine label
        if duration_days == 30:
            label = "MENSUAL"
        elif duration_days == 365:
            label = "ANUAL"
        else:
            label = f"{duration_days} DÍAS"
        
        # Add default option
        await add_option(sku, label, price_mxn, duration_days)
        synced += 1
    
    return synced
