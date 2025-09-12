#!/bin/bash

# ONZA Bot - Script de Instalación Mejorado
# Instala y configura el bot automáticamente

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 ONZA Bot - Instalador Mejorado${NC}"
echo "=================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ No ejecutes este script como root${NC}"
    echo "Ejecuta: bash install.sh"
    exit 1
fi

# Get current directory
BOT_DIR=$(pwd)
echo -e "${BLUE}📁 Directorio del bot: $BOT_DIR${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "📝 Creando archivo .env desde env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Archivo .env creado${NC}"
        echo -e "${YELLOW}📝 IMPORTANTE: Edita el archivo .env con tus configuraciones:${NC}"
        echo "   nano .env"
        echo ""
        echo -e "${YELLOW}Variables requeridas:${NC}"
        echo "   - DISCORD_TOKEN"
        echo "   - GUILD_ID"
        echo "   - STAFF_ROLE_ID"
        echo ""
        read -p "Presiona Enter cuando hayas configurado el archivo .env..."
    else
        echo -e "${RED}❌ Archivo env.example no encontrado${NC}"
        exit 1
    fi
fi

# Load environment variables
echo "📋 Cargando variables de entorno..."
source .env

# Check required variables
REQUIRED_VARS=("DISCORD_TOKEN" "GUILD_ID")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Error: Variable $var no configurada en .env${NC}"
        echo "Edita el archivo .env y configura todas las variables requeridas"
        exit 1
    fi
done

echo -e "${GREEN}✅ Variables de entorno verificadas${NC}"

# Create necessary directories
echo "📁 Creando directorios necesarios..."
mkdir -p data logs backups

# Install Python dependencies
echo "📦 Instalando dependencias de Python..."
if command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r requirements.txt
else
    echo -e "${RED}❌ pip no encontrado. Instala Python y pip primero.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencias instaladas${NC}"

# Test bot configuration
echo "🧪 Probando configuración del bot..."
python3 -c "
import sys
sys.path.append('.')
try:
    from config import *
    print('✅ Configuración cargada correctamente')
except Exception as e:
    print(f'❌ Error en configuración: {e}')
    sys.exit(1)
"

# Create systemd service
echo "⚙️  Creando servicio systemd..."
SERVICE_FILE="/etc/systemd/system/onza-bot.service"

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=ONZA Discord Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Servicio systemd creado${NC}"

# Reload systemd and enable service
echo "🔄 Configurando servicio systemd..."
sudo systemctl daemon-reload
sudo systemctl enable onza-bot

echo -e "${GREEN}✅ Servicio habilitado${NC}"

# Create backup script
echo "💾 Creando script de backup..."
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
BOT_DIR="."

mkdir -p $BACKUP_DIR
if [ -f "$BOT_DIR/data/onza_bot.db" ]; then
    cp "$BOT_DIR/data/onza_bot.db" "$BACKUP_DIR/backup_$DATE.db"
    echo "Backup creado: backup_$DATE.db"
fi

# Limpiar backups antiguos (más de 7 días)
find $BACKUP_DIR -name "backup_*.db" -mtime +7 -delete
EOF

chmod +x backup.sh

# Create monitoring script
echo "📊 Creando script de monitoreo..."
cat > monitor.sh << 'EOF'
#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    if systemctl is-active --quiet onza-bot; then
        echo -e "${GREEN}✅ Bot está ejecutándose${NC}"
        return 0
    else
        echo -e "${RED}❌ Bot no está ejecutándose${NC}"
        return 1
    fi
}

check_logs() {
    ERROR_COUNT=$(journalctl -u onza-bot --since "1 hour ago" | grep -c "ERROR\|CRITICAL" || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Se encontraron $ERROR_COUNT errores en la última hora${NC}"
        return 1
    else
        echo -e "${GREEN}✅ No hay errores recientes${NC}"
        return 0
    fi
}

echo "🔍 Verificando estado del bot..."
check_service
check_logs

if ! check_service; then
    echo "🔄 Reiniciando bot..."
    sudo systemctl restart onza-bot
    sleep 5
    check_service
fi
EOF

chmod +x monitor.sh

echo -e "${GREEN}✅ Scripts de monitoreo creados${NC}"

# Final instructions
echo ""
echo -e "${GREEN}🎉 ¡Instalación completada!${NC}"
echo "=================================="
echo ""
echo -e "${BLUE}📋 Comandos útiles:${NC}"
echo "   Iniciar bot:     sudo systemctl start onza-bot"
echo "   Detener bot:     sudo systemctl stop onza-bot"
echo "   Reiniciar bot:   sudo systemctl restart onza-bot"
echo "   Ver estado:      sudo systemctl status onza-bot"
echo "   Ver logs:        sudo journalctl -u onza-bot -f"
echo "   Monitorear:      ./monitor.sh"
echo "   Backup:          ./backup.sh"
echo ""
echo -e "${YELLOW}🚀 Para iniciar el bot ahora:${NC}"
echo "   sudo systemctl start onza-bot"
echo ""
echo -e "${YELLOW}📝 Para ver los logs en tiempo real:${NC}"
echo "   sudo journalctl -u onza-bot -f"
echo ""
echo -e "${GREEN}✅ El bot se iniciará automáticamente al reiniciar el servidor${NC}"
echo ""
echo -e "${BLUE}📚 Documentación completa en: README.md${NC}"
