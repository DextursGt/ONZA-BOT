# ONZA-BOT Web Dashboard

## Descripción

Dashboard web interactivo para controlar ONZA-BOT desde el navegador.

## Características

- ✅ **Envío de mensajes de texto** a cualquier canal
- ✅ **Creación de embeds** con vista previa en tiempo real
- ✅ **Monitoreo del bot** (estado, latencia, servidores)
- ✅ **Selección de canales** por categorías
- ✅ **Autenticación HTTP Basic**
- ✅ **Interfaz responsive** con Bootstrap 5

## Instalación

1. Instalar dependencias:
```bash
pip3 install -r requirements-dashboard.txt
```

2. Configurar credenciales en `.env`:
```bash
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=tu-contraseña-segura
DASHBOARD_PORT=8000
```

3. Iniciar con pm2:
```bash
pm2 start ecosystem.config.js
pm2 save
```

## Acceso

Abrir en navegador: `http://tu-servidor-ip:8000`

Credenciales: Las configuradas en `.env`

## Uso

### Enviar Mensaje de Texto

1. Seleccionar canal de destino
2. Escribir mensaje
3. Click en "Enviar Mensaje"

### Crear Embed

1. Ir a pestaña "Mensaje Embed"
2. Seleccionar canal
3. Completar título y descripción
4. Personalizar color, footer, imagen (opcional)
5. Ver vista previa en tiempo real
6. Click en "Enviar Embed"

## API Endpoints

- `GET /health` - Health check
- `GET /api/bot/status` - Estado del bot
- `GET /api/channels/{guild_id}` - Lista de canales
- `POST /api/message/send` - Enviar mensaje de texto
- `POST /api/message/embed` - Enviar embed

## Seguridad

- Autenticación HTTP Basic
- HTTPS recomendado en producción
- No exponer puerto 8000 directamente a internet
- Usar reverse proxy (nginx/traefik)

## Troubleshooting

**Dashboard no carga:**
- Verificar que pm2 está corriendo: `pm2 status`
- Revisar logs: `pm2 logs ONZA-DASHBOARD`

**Bot aparece offline:**
- Verificar que ONZA-BOT está corriendo
- Revisar que main.py importa bot_api

**No se puede enviar mensajes:**
- Verificar permisos del bot en Discord
- Revisar logs del bot: `pm2 logs ONZA-BOT`
