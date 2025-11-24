#!/bin/bash

# Script de despliegue rápido para Hostinger VPS
# Uso: ./deploy.sh

echo "🚀 Iniciando despliegue de ONZA-BOT a Hostinger..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuración
SERVER="root@193.43.134.31"
REMOTE_DIR="/root/ONZA-BOT"

echo -e "${YELLOW}📤 Subiendo archivos al servidor...${NC}"

# Subir archivos usando rsync (más eficiente que scp)
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.env' --exclude='.fortnite_key' --exclude='*.log' --exclude='data/' \
  ./ $SERVER:$REMOTE_DIR/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Archivos subidos correctamente${NC}"
else
    echo -e "${RED}❌ Error subiendo archivos${NC}"
    exit 1
fi

echo -e "${YELLOW}🔧 Ejecutando comandos en el servidor...${NC}"

# Ejecutar comandos en el servidor
ssh $SERVER << 'ENDSSH'
cd /root/ONZA-BOT

echo "📦 Instalando/actualizando dependencias..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "🔄 Reiniciando servicio (si existe)..."
if systemctl is-active --quiet onza-bot; then
    systemctl restart onza-bot
    echo "✅ Servicio reiniciado"
else
    echo "ℹ️  Servicio no está activo. Inicia manualmente con: systemctl start onza-bot"
fi

echo "📊 Estado del servicio:"
systemctl status onza-bot --no-pager -l || echo "Servicio no configurado aún"

ENDSSH

echo -e "${GREEN}✅ Despliegue completado!${NC}"
echo -e "${YELLOW}💡 Para ver logs: ssh $SERVER 'journalctl -u onza-bot -f'${NC}"
