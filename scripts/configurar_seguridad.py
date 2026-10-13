"""Una sola vez (idempotente): canal #registro-servidor en 🔒 Staff y reglas de AutoMod contra estafas.

Uso, en /root/ONZA-BOT:  python3 scripts/configurar_seguridad.py
Imprime SERVER_LOG_CHANNEL_ID para ponerlo en .env.
"""
import json
import os
import time
import urllib.request

from dotenv import load_dotenv

load_dotenv()
TOK, G = os.environ["DISCORD_TOKEN"], os.environ["GUILD_ID"]
MOTIVO = "Configuración de seguridad del bot"
CATEGORIA_STAFF = "🔒 Staff"
CANAL_REGISTRO = "registro-servidor"
ROLES_EXENTOS = {"Owner", "Bot", "Operaciones", "Moderador", "Soporte", "Dev"}

# Frases de estafa típicas en servidores de tiendas digitales. Se bloquea el mensaje y se avisa al staff.
FRASES_ESTAFA = [
    "free nitro", "nitro free", "nitro gratis", "nitro gratuito", "free discord nitro",
    "steam gift", "free steam", "free robux", "free vbucks", "airdrop",
]
# Dominios que imitan a Discord o Steam (Rust regex, sin lookarounds).
REGEX_DOMINIOS = [
    r"d[il1]sc[o0]r[cdl]{1,2}-?(nitro|gift|gifts|app)\.(ru|xyz|top|click|fun|site|online|shop|store|link|com)",
    r"d[l1]sc[o0]rd\.(com|gift|gg)",
    r"disc[o0]rcl\.",
    r"steamcommun[il1l]ty\.(ru|com\.ru|net|xyz)",
    r"steamcommunlty\.",
]


def api(metodo, ruta, cuerpo=None):
    time.sleep(0.3)
    r = urllib.request.Request("https://discord.com/api/v10" + ruta, method=metodo,
                               data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                               headers={"Authorization": "Bot " + TOK, "User-Agent": "DiscordBot (onza,1)",
                                        "Content-Type": "application/json", "X-Audit-Log-Reason": MOTIVO})
    return json.load(urllib.request.urlopen(r))


canales = api("GET", f"/guilds/{G}/channels")
categoria = next(c for c in canales if c["type"] == 4 and c["name"] == CATEGORIA_STAFF)
registro = next((c for c in canales if c["name"] == CANAL_REGISTRO and c.get("parent_id") == categoria["id"]), None)
if not registro:
    registro = api("POST", f"/guilds/{G}/channels", {
        "name": CANAL_REGISTRO, "type": 0, "parent_id": categoria["id"],
        "topic": "Registro automático: mensajes borrados/editados, roles, entradas/salidas, baneos, AutoMod y anti-raid.",
        "permission_overwrites": categoria.get("permission_overwrites", []),
    })
    print("canal creado")
print(f"SERVER_LOG_CHANNEL_ID={registro['id']}")

exentos = [r["id"] for r in api("GET", f"/guilds/{G}/roles") if r["name"] in ROLES_EXENTOS]
reglas = {r["name"]: r for r in api("GET", f"/guilds/{G}/auto-moderation/rules")}
acciones = [
    {"type": 1, "metadata": {"custom_message": "Mensaje bloqueado: parece una estafa. Si es un error, abre un ticket."}},
    {"type": 2, "metadata": {"channel_id": registro["id"]}},
]
regla = {
    "name": "Estafas (nitro/robux/steam falsos)", "event_type": 1, "trigger_type": 1,
    "trigger_metadata": {"keyword_filter": FRASES_ESTAFA, "regex_patterns": REGEX_DOMINIOS},
    "actions": acciones, "enabled": True, "exempt_roles": exentos,
}
if regla["name"] in reglas:
    api("PATCH", f"/guilds/{G}/auto-moderation/rules/{reglas[regla['name']]['id']}",
        {k: regla[k] for k in ("trigger_metadata", "actions", "enabled", "exempt_roles")})
    print("regla de estafas actualizada")
else:
    api("POST", f"/guilds/{G}/auto-moderation/rules", regla)
    print("regla de estafas creada")

# Las 2 reglas que ya existían también avisan en el registro (sin cambiar qué bloquean).
for nombre, r in reglas.items():
    if nombre != regla["name"] and not any(a["type"] == 2 for a in r["actions"]):
        api("PATCH", f"/guilds/{G}/auto-moderation/rules/{r['id']}", {"actions": r["actions"] + [acciones[1]]})
        print("aviso al registro agregado a:", nombre)
