import os
from dotenv import load_dotenv
import nextcord

# Cargar variables de entorno
load_dotenv()

# Configuración del bot
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
BRAND_NAME = os.getenv('BRAND_NAME', 'ONZA Bot')

# Configuración de roles
OWNER_ROLE_ID = int(os.getenv('OWNER_ROLE_ID', 0))
STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID', 0))
SUPPORT_ROLE_ID = int(os.getenv('SUPPORT_ROLE_ID', 0))

# Discord user IDs
OWNER_DISCORD_ID = int(os.getenv('OWNER_DISCORD_ID', 857134594028601364))

# Configuración de canales
TICKET_CHANNEL_ID = int(os.getenv('TICKET_CHANNEL_ID', 0))
TICKETS_LOG_CHANNEL_ID = int(os.getenv('TICKETS_LOG_CHANNEL_ID', 0))
SERVER_LOG_CHANNEL_ID = int(os.getenv('SERVER_LOG_CHANNEL_ID', 0))
TICKETS_CATEGORY_NAME = os.getenv('TICKETS_CATEGORY_NAME', '🎫 Tickets')

# Integración con onzalatam.com (API de solo lectura /api/bot/*)
WEB_URL = os.getenv('WEB_URL', 'https://onzalatam.com').rstrip('/')
WEB_BOT_TOKEN = os.getenv('WEB_BOT_TOKEN', '')

# Configuración de archivos
DATA_FILE = os.getenv('DATA_FILE', 'data/bot_data.json')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/onza_bot.db')

# Configuración de idioma
DEFAULT_LOCALE = os.getenv('DEFAULT_LOCALE', 'es')

# Configuración de Roblox
ROBLOX_GROUP_ID = int(os.getenv('ROBLOX_GROUP_ID', 0))
ROBLOX_API_BASE = 'https://users.roblox.com/v1'
ROBLOX_GROUPS_API = 'https://groups.roblox.com/v1'

# Configuración de intents
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True
