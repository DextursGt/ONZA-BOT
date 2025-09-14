import os
from dotenv import load_dotenv
import discord

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

# Configuración de canales
TICKET_CHANNEL_ID = int(os.getenv('TICKET_CHANNEL_ID', 0))
TICKETS_LOG_CHANNEL_ID = int(os.getenv('TICKETS_LOG_CHANNEL_ID', 0))
TICKETS_CATEGORY_NAME = os.getenv('TICKETS_CATEGORY_NAME', '🎫 Tickets')

# Configuración de archivos
DATA_FILE = os.getenv('DATA_FILE', 'data/bot_data.json')

# Configuración de Fortnite API
FORTNITE_API_KEY = os.getenv('FORTNITE_API_KEY', '')
FORTNITE_API_URL = 'https://fortnite-api.com/v2'
FORTNITE_HEADERS = {
    'Authorization': FORTNITE_API_KEY,
    'Content-Type': 'application/json'
} if FORTNITE_API_KEY else {}

# Configuración de Roblox
ROBLOX_GROUP_ID = int(os.getenv('ROBLOX_GROUP_ID', 0))
ROBLOX_API_BASE = 'https://users.roblox.com/v1'
ROBLOX_GROUPS_API = 'https://groups.roblox.com/v1'

# Configuración de intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True
