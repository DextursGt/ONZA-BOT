"""Cliente de la API de solo lectura de onzalatam.com (/api/bot/*).

La web nunca llama al bot: el bot pregunta. Si la web no responde, el bot sigue funcionando
y los precios de Robux mandan al cliente a la página en vez de inventar una cifra.
"""
import asyncio
import logging

import aiohttp

from config import WEB_URL, WEB_BOT_TOKEN

log = logging.getLogger('onza-bot')
TIMEOUT = aiohttp.ClientTimeout(total=5)
ESTADOS_FINALES = ("entregado", "cancelado")


async def _get(ruta: str, params: dict = None):
    """JSON de la web, o None si no hay token, no responde o responde con error."""
    if not WEB_BOT_TOKEN:
        return None
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as sesion:
            async with sesion.get(f"{WEB_URL}{ruta}", params=params,
                                  headers={"Authorization": f"Bearer {WEB_BOT_TOKEN}"}) as r:
                if r.status != 200:
                    log.warning(f"Web {ruta} respondió {r.status}")
                    return None
                return await r.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        log.warning(f"Web {ruta} no respondió: {e}")
        return None


async def catalogo():
    return await _get("/api/bot/catalogo")


async def pedidos_desde(desde: str):
    datos = await _get("/api/bot/pedidos", {"desde": desde})
    return None if datos is None else datos.get("pedidos", [])


def _pesos(valor) -> str:
    return f"${valor:,.0f}" if float(valor).is_integer() else f"${valor:,.2f}"


def texto_robux(cat) -> str:
    """Campo de Robux del ticket con los precios que publica /roblox (un dato, una fuente)."""
    pedir = "**Responde:** cantidad RBX + usuario Roblox y método de pago"
    robux = (cat or {}).get("robux")
    if not robux:
        return f"{pedir}\n\nPrecios actualizados: {WEB_URL}/roblox"
    tabla = "\n".join(
        f"• {f['cantidad']:,} RBX: {_pesos(f['pesosBase'])}" + (" (promo)" if f.get("esPromo") else "")
        for f in robux["tabla"]
    )
    return (
        f"{pedir}\n\n"
        f"**Precio:** {_pesos(robux['porMillar'])} por 1,000 RBX con transferencia u OXXO; "
        f"{_pesos(robux['porMillarPaypal'])} con PayPal\n"
        + (f"{tabla}\n" if tabla else "")
        + f"\n**Requisito:** unirte 15 días antes al grupo\n**Grupo:** {robux['grupo']}\n"
        f"Más detalles: {robux['pagina']}"
    )
