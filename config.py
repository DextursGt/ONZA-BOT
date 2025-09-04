"""
Configuration module for ONZA Bot
Centralizes all bot configuration and environment variables
"""
import os
from typing import List

# Helpers para ENV
def env_bool(key: str, default: bool = False) -> bool:
    """Convert environment variable to boolean"""
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')

def env_list(key: str, default: str = "") -> List[str]:
    """Convert comma-separated environment variable to list"""
    value = os.getenv(key, default)
    return [x.strip() for x in value.split(',') if x.strip()]

def env_int(key: str, default: int = 0) -> int:
    """Convert environment variable to integer"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = env_int("GUILD_ID", 0)

# Role IDs
SUPPORT_ROLE_ID = env_int("SUPPORT_ROLE_ID", 0)
STAFF_ROLE_ID = env_int("STAFF_ROLE_ID", SUPPORT_ROLE_ID)
CLIENT_ROLE_ID = env_int("CLIENT_ROLE_ID", 1408126690315473117)
VIP_ROLE_IDS = [int(x) for x in env_list("VIP_ROLE_IDS", "0") if x != "0"]

# Channel IDs
TICKETS_CATEGORY_NAME = os.getenv("TICKETS_CATEGORY_NAME", "Soporte")
TICKETS_LOG_CHANNEL_ID = env_int("TICKETS_LOG_CHANNEL_ID", 0)
STORE_CATALOG_CHANNEL_ID = env_int("STORE_CATALOG_CHANNEL_ID", 0)
STORE_OFFERS_CHANNEL_ID = env_int("STORE_OFFERS_CHANNEL_ID", 0)
STORE_PRICES_CHANNEL_ID = env_int("STORE_PRICES_CHANNEL_ID", 0)
REVIEWS_CHANNEL_ID = env_int("REVIEWS_CHANNEL_ID", 0)
PAYMENTS_LOG_CHANNEL_ID = env_int("PAYMENTS_LOG_CHANNEL_ID", 0)
DELIVERIES_LOG_CHANNEL_ID = env_int("DELIVERIES_LOG_CHANNEL_ID", 0)
REFERRALS_LOG_CHANNEL_ID = env_int("REFERRALS_LOG_CHANNEL_ID", 0)
WELCOME_CHANNEL_ID = env_int("WELCOME_CHANNEL_ID", 1413231178814722151)
HOW_TO_BUY_CHANNEL_ID = env_int("HOW_TO_BUY_CHANNEL_ID", 1408131623270223872)

# Bot Settings
BRAND_NAME = os.getenv("BRAND_NAME", "ONZA")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "es")
DATABASE_PATH = os.getenv("DATABASE_PATH", "onza_bot.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")
WEBHOOK_PORT = env_int("WEBHOOK_PORT", 8080)

# Render Configuration
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")

# AI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# Payment Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")

# Business Settings
FRAUD_THRESHOLD = env_int("FRAUD_THRESHOLD", 75)
WARRANTY_DEFAULT_DAYS = env_int("WARRANTY_DEFAULT_DAYS", 7)

# Default Content
DEFAULT_CATALOG = os.getenv("DEFAULT_CATALOG", 
"""Spotify Premium — desde $115/mes
Netflix — desde $219/mes
Discord Nitro — desde $99/mes
Gift Cards / Top-ups — consultar
Abrir ticket en #abrir-ticket""").strip()

DEFAULT_OFFERS = os.getenv("DEFAULT_OFFERS",
"""Semana 1: -15% primeras 50 órdenes
Referidos: saldo por cada amigo""").strip()

DEFAULT_PRICES = os.getenv("DEFAULT_PRICES",
"""Servicio | Mensual | Trimestral | Anual
Spotify | $115 | $310 | $1,150
Netflix | $219 | $590 | $2,190
Nitro   | $99  | $270 | $990""").strip()

# Message Markers
MK_CATALOG = "[ONZA:CATALOGO]"
MK_OFFERS = "[ONZA:OFERTAS]"
MK_PRICES = "[ONZA:PRECIOS]"

# Database Configuration
MIGRATIONS = [
    # Migration 1: Tablas base
    """
    CREATE TABLE IF NOT EXISTS users (
        discord_id INTEGER PRIMARY KEY,
        username TEXT,
        lang TEXT DEFAULT 'es',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        flags TEXT DEFAULT '{}',
        vip_tier INTEGER DEFAULT 0,
        vip_expires_at TIMESTAMP,
        referral_code TEXT UNIQUE,
        referred_by TEXT,
        fraud_score INTEGER DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price_cents INTEGER NOT NULL,
        currency TEXT DEFAULT 'MXN',
        duration_days INTEGER,
        warranty_days INTEGER,
        stock_type TEXT DEFAULT 'manual',
        delivery_meta TEXT DEFAULT '{}',
        active BOOLEAN DEFAULT 1
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        product_id INTEGER,
        amount_cents INTEGER NOT NULL,
        currency TEXT DEFAULT 'USD',
        status TEXT DEFAULT 'pending',
        provider TEXT,
        provider_session_id TEXT,
        transaction_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        paid_at TIMESTAMP,
        delivered_at TIMESTAMP,
        expires_at TIMESTAMP,
        warranty_until TIMESTAMP,
        coupon_id INTEGER,
        referral_code_used TEXT,
        notes TEXT DEFAULT '{}',
        FOREIGN KEY (user_id) REFERENCES users(discord_id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_channel_id INTEGER UNIQUE,
        user_id INTEGER NOT NULL,
        order_id TEXT,
        status TEXT DEFAULT 'open',
        escalated BOOLEAN DEFAULT 0,
        assigned_to INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        last_action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(discord_id),
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ticket_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        user_id INTEGER,
        data TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id),
        FOREIGN KEY (user_id) REFERENCES users(discord_id)
    );
    """,
    # Índices
    "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);"
]
