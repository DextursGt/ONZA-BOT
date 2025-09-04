# ========== CONFIGURACIÓN OPTIMIZADA DEL BOT ==========

# Configuración de rendimiento
BOT_CONFIG = {
    "max_concurrent_requests": 10,
    "request_timeout": 30,
    "heartbeat_timeout": 60,
    "enable_logging": True,
    "log_level": "INFO",
    "auto_reconnect": True,
    "rate_limit_delay": 1.0
}

# Configuración de canales automáticos
CHANNEL_PATTERNS = {
    "anuncios": ["anuncio", "announcement", "general", "main"],
    "logs": ["log", "logs", "admin", "mod"],
    "tickets": ["ticket", "tickets", "soporte", "support"],
    "reglas": ["reglas", "rules", "info", "informacion"],
    "bienvenida": ["bienvenida", "welcome", "entrada"]
}

# Configuración de métodos de pago
DEFAULT_PAYMENT_METHODS = [
    "💳 **Transferencia Bancaria**",
    "📱 **Klar** - Transferencia instantánea",
    "🟣 **Nu** - Transferencia bancaria",
    "🟡 **Bybit** - Criptomonedas",
    "🟠 **Binance** - Criptomonedas",
    "🟢 **Mercado Pago** - Transferencia",
    "💸 **Efectivo** - En persona"
]

# Configuración de colores para embeds
EMBED_COLORS = {
    "azul": 0x5865F2,
    "verde": 0x57F287,
    "rojo": 0xED4245,
    "amarillo": 0xFEE75C,
    "morado": 0x800080,
    "naranja": 0xFFA500,
    "default": 0x5865F2
}

# Configuración de timeouts
TIMEOUTS = {
    "view_timeout": 120,
    "modal_timeout": 300,
    "interaction_timeout": 15
}
