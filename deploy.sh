#!/bin/bash

# ONZA Bot Deployment Script
# Para hosting 24/7

set -e

echo "🚀 ONZA Bot - Script de Despliegue"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: Archivo .env no encontrado${NC}"
    echo "📝 Copia env.example a .env y configura tus variables:"
    echo "   cp env.example .env"
    echo "   nano .env"
    exit 1
fi

# Load environment variables
echo "📋 Cargando variables de entorno..."
source .env

# Check required variables
REQUIRED_VARS=("DISCORD_TOKEN" "GUILD_ID" "STAFF_ROLE_ID")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Error: Variable $var no configurada en .env${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Variables de entorno verificadas${NC}"

# Create necessary directories
echo "📁 Creando directorios necesarios..."
mkdir -p data logs backups

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker no está instalado${NC}"
    echo "📦 Instala Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose no está instalado${NC}"
    echo "📦 Instala Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker y Docker Compose verificados${NC}"

# Build and start services
echo "🔨 Construyendo imagen Docker..."
docker-compose build --no-cache

echo "🚀 Iniciando servicios..."
docker-compose up -d

# Wait for bot to start
echo "⏳ Esperando que el bot se inicie..."
sleep 10

# Check status
echo "📊 Verificando estado del bot..."
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Bot iniciado correctamente!${NC}"
    echo ""
    echo "📋 Comandos útiles:"
    echo "   Ver logs: docker-compose logs -f onza-bot"
    echo "   Detener: docker-compose down"
    echo "   Reiniciar: docker-compose restart"
    echo "   Estado: docker-compose ps"
    echo ""
    echo "🌐 El bot está ejecutándose 24/7 en el host"
else
    echo -e "${RED}❌ Error al iniciar el bot${NC}"
    echo "📋 Revisa los logs:"
    echo "   docker-compose logs onza-bot"
    exit 1
fi
