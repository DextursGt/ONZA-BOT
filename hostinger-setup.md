# ONZA Bot - Configuración para Hostinger VPS

## Pasos para desplegar en Hostinger VPS

### 1. Preparación del VPS

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias necesarias
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Instalar Docker (opcional, para contenedores)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Configuración del Bot

```bash
# Clonar o subir el código del bot
git clone <tu-repositorio> onza-bot
cd onza-bot

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
nano .env
```

### 3. Variables de Entorno (.env)

```env
# Discord Configuration
DISCORD_TOKEN=tu_token_discord_aqui
GUILD_ID=tu_guild_id_aqui

# Roles
STAFF_ROLE_ID=tu_staff_role_id
SUPPORT_ROLE_ID=tu_support_role_id
CLIENT_ROLE_ID=tu_client_role_id

# Channels (opcional, se pueden configurar después)
TICKETS_LOG_CHANNEL_ID=0
STORE_CATALOG_CHANNEL_ID=0
REVIEWS_CHANNEL_ID=0

# Bot Settings
BRAND_NAME=ONZA
DEFAULT_LOCALE=es
DATABASE_PATH=./data/onza_bot.db

# AI (opcional)
OPENAI_API_KEY=tu_openai_key_aqui

# Payment (opcional)
STRIPE_SECRET_KEY=tu_stripe_key_aqui
MP_ACCESS_TOKEN=tu_mercadopago_token_aqui
```

### 4. Ejecución del Bot

#### Opción A: Ejecución Directa (Recomendada para VPS)

```bash
# Crear directorios necesarios
mkdir -p data logs backups

# Ejecutar el bot
python main.py
```

#### Opción B: Con Docker

```bash
# Construir y ejecutar con Docker Compose
docker-compose up -d

# Ver logs
docker-compose logs -f onza-bot
```

### 5. Configuración de Systemd (Para ejecución automática)

```bash
# Crear servicio systemd
sudo nano /etc/systemd/system/onza-bot.service
```

Contenido del archivo de servicio:

```ini
[Unit]
Description=ONZA Discord Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/onza-bot
Environment=PATH=/ruta/a/onza-bot/venv/bin
ExecStart=/ruta/a/onza-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Habilitar y iniciar el servicio
sudo systemctl daemon-reload
sudo systemctl enable onza-bot
sudo systemctl start onza-bot

# Ver estado
sudo systemctl status onza-bot

# Ver logs
sudo journalctl -u onza-bot -f
```

### 6. Monitoreo

```bash
# Ejecutar script de monitoreo
chmod +x monitor.sh
./monitor.sh
```

### 7. Comandos Útiles

```bash
# Ver logs del bot
tail -f logs/onza_bot.log

# Reiniciar bot (si usa systemd)
sudo systemctl restart onza-bot

# Reiniciar bot (si usa Docker)
docker-compose restart onza-bot

# Ver estado del bot
sudo systemctl status onza-bot
# o
docker-compose ps

# Actualizar bot
git pull
sudo systemctl restart onza-bot
```

### 8. Configuración de Firewall (si es necesario)

```bash
# Abrir puertos necesarios (solo si usas webhooks)
sudo ufw allow 8080
sudo ufw enable
```

### 9. Backup Automático

```bash
# Crear script de backup
nano backup.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/ruta/a/backups"
BOT_DIR="/ruta/a/onza-bot"

mkdir -p $BACKUP_DIR
cp $BOT_DIR/data/*.db $BACKUP_DIR/backup_$DATE.db
find $BACKUP_DIR -name "backup_*.db" -mtime +7 -delete
```

```bash
# Hacer ejecutable y programar en crontab
chmod +x backup.sh
crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * /ruta/a/onza-bot/backup.sh
```

## Notas Importantes

1. **Keep-alive eliminado**: Ya no es necesario el servidor web Flask para mantener el bot activo
2. **VPS dedicado**: Hostinger VPS mantiene el bot activo 24/7 sin necesidad de keep-alive
3. **Recursos**: El bot consume muy pocos recursos, ideal para VPS básico
4. **Seguridad**: Mantén tu token de Discord seguro y nunca lo compartas
5. **Logs**: Revisa regularmente los logs para detectar problemas

## Solución de Problemas

### Bot no se conecta
- Verifica que el token de Discord sea correcto
- Revisa que el bot tenga los permisos necesarios en Discord
- Verifica la conexión a internet del VPS

### Bot se desconecta frecuentemente
- Revisa los logs para errores
- Verifica que el VPS tenga recursos suficientes
- Considera usar systemd para reinicio automático

### Comandos no funcionan
- Verifica que GUILD_ID esté configurado correctamente
- Revisa que el bot tenga permisos en el servidor
- Sincroniza los comandos slash manualmente si es necesario
