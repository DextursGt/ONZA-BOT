"""Dashboard configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

# Dashboard settings
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 8000))
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change-me-in-production")

# Bot settings (from main .env)
GUILD_ID = int(os.getenv("GUILD_ID", 0))
