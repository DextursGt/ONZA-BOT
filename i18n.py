"""
Internationalization module for ONZA Bot
Handles translations and language support
"""
from typing import Optional
import aiosqlite
from config import DEFAULT_LOCALE, DATABASE_PATH

# Translations dictionary
translations = {
    "es": {
        "common.ok": "✅ Listo",
        "common.error": "❌ Error: {error}",
        "common.loading": "⏳ Procesando...",
        "common.not_found": "No encontrado",
        "errors.only_staff": "❌ Solo el staff puede usar este comando.",
        "errors.invalid_input": "❌ Entrada inválida. Por favor verifica los datos.",
        "errors.db_error": "❌ Error de base de datos. Contacta al administrador.",
        "tickets.created": "✅ Ticket creado: {channel}",
        "tickets.closed": "🔒 Ticket cerrado por {user}",
        "tickets.escalated": "⚠️ Ticket escalado al staff",
        "tickets.resolved": "✅ Ticket marcado como resuelto",
        "verify.start": "🔍 Verificando tu compra...",
        "verify.success": "✅ Compra verificada. Rol asignado.",
        "verify.not_found": "❌ No se encontró una orden con ese ID.",
        "verify.manual": "📋 Tu verificación requiere revisión manual. Se ha creado un ticket.",
        "review.thanks": "⭐ Gracias por tu reseña. Será revisada por el staff.",
        "review.approved": "✅ Tu reseña ha sido aprobada y publicada.",
        "review.already": "❌ Ya has dejado una reseña para este producto.",
        "payment.creating": "💳 Creando sesión de pago...",
        "payment.success": "✅ Pago confirmado para orden #{order_id}",
        "payment.failed": "❌ El pago falló o fue cancelado.",
        "delivery.sending": "📦 Enviando tu producto...",
        "delivery.sent": "✅ Producto entregado. Revisa tu DM.",
        "delivery.failed": "❌ Error al entregar. Contacta soporte.",
        "renewal.reminder": "⏰ Tu servicio {service} expira en {days} días.",
        "renewal.expired": "❌ Tu servicio {service} ha expirado.",
        "referral.generated": "🎯 Tu código de referido: `{code}`",
        "referral.used": "✅ Código de referido aplicado.",
        "referral.invalid": "❌ Código de referido inválido.",
        "warranty.valid": "✅ Garantía válida hasta {date}",
        "warranty.expired": "❌ La garantía ha expirado.",
        "warranty.claimed": "📋 Reclamo de garantía creado.",
        "language.changed": "✅ Idioma cambiado a Español",
        "commands.help": "📋 Lista de comandos disponibles"
    },
    "en": {
        "common.ok": "✅ Done",
        "common.error": "❌ Error: {error}",
        "common.loading": "⏳ Processing...",
        "common.not_found": "Not found",
        "errors.only_staff": "❌ Only staff can use this command.",
        "errors.invalid_input": "❌ Invalid input. Please check your data.",
        "errors.db_error": "❌ Database error. Contact administrator.",
        "tickets.created": "✅ Ticket created: {channel}",
        "tickets.closed": "🔒 Ticket closed by {user}",
        "tickets.escalated": "⚠️ Ticket escalated to staff",
        "tickets.resolved": "✅ Ticket marked as resolved",
        "verify.start": "🔍 Verifying your purchase...",
        "verify.success": "✅ Purchase verified. Role assigned.",
        "verify.not_found": "❌ No order found with that ID.",
        "verify.manual": "📋 Your verification requires manual review. A ticket has been created.",
        "review.thanks": "⭐ Thanks for your review. It will be reviewed by staff.",
        "review.approved": "✅ Your review has been approved and published.",
        "review.already": "❌ You've already reviewed this product.",
        "payment.creating": "💳 Creating payment session...",
        "payment.success": "✅ Payment confirmed for order #{order_id}",
        "payment.failed": "❌ Payment failed or was cancelled.",
        "delivery.sending": "📦 Sending your product...",
        "delivery.sent": "✅ Product delivered. Check your DM.",
        "delivery.failed": "❌ Delivery error. Contact support.",
        "renewal.reminder": "⏰ Your {service} service expires in {days} days.",
        "renewal.expired": "❌ Your {service} service has expired.",
        "referral.generated": "🎯 Your referral code: `{code}`",
        "referral.used": "✅ Referral code applied.",
        "referral.invalid": "❌ Invalid referral code.",
        "warranty.valid": "✅ Warranty valid until {date}",
        "warranty.expired": "❌ Warranty has expired.",
        "warranty.claimed": "📋 Warranty claim created.",
        "language.changed": "✅ Language changed to English",
        "commands.help": "📋 List of available commands"
    }
}

async def t(key: str, lang: str = None, **kwargs) -> str:
    """Traducir una clave con parámetros opcionales"""
    if not lang:
        lang = DEFAULT_LOCALE
    
    # Buscar traducción
    translation = translations.get(lang, {}).get(key)
    if not translation:
        translation = translations.get("es", {}).get(key, f"[{key}]")
    
    # Formatear con parámetros
    try:
        return translation.format(**kwargs)
    except:
        return translation

async def get_user_lang(user_id: int) -> str:
    """Obtener idioma preferido del usuario"""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT lang FROM users WHERE discord_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else DEFAULT_LOCALE
    except Exception:
        return DEFAULT_LOCALE
