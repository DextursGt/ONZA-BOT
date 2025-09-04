#!/bin/bash

# ONZA Bot Monitoring Script
# Para monitoreo 24/7

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOT_NAME="onza-bot"
LOG_FILE="logs/monitor.log"
CHECK_INTERVAL=300  # 5 minutes

# Create logs directory if it doesn't exist
mkdir -p logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_bot_status() {
    if docker ps | grep -q "$BOT_NAME"; then
        # Check if container is running
        if docker inspect "$BOT_NAME" | grep -q '"Status": "running"'; then
            log "${GREEN}✅ Bot está ejecutándose correctamente${NC}"
            return 0
        else
            log "${RED}❌ Bot está detenido${NC}"
            return 1
        fi
    else
        log "${RED}❌ Contenedor del bot no encontrado${NC}"
        return 1
    fi
}

check_bot_health() {
    if docker inspect "$BOT_NAME" | grep -q '"Health": "healthy"'; then
        log "${GREEN}✅ Bot está saludable${NC}"
        return 0
    else
        log "${YELLOW}⚠️  Bot no está saludable${NC}"
        return 1
    fi
}

check_database() {
    if [ -f "data/onza_bot.db" ]; then
        log "${GREEN}✅ Base de datos principal encontrada${NC}"
        return 0
    else
        log "${RED}❌ Base de datos principal no encontrada${NC}"
        return 1
    fi
}

check_logs() {
    # Check for recent errors in logs
    if [ -f "logs/onza_bot.log" ]; then
        ERROR_COUNT=$(tail -100 logs/onza_bot.log | grep -c "ERROR\|CRITICAL" || echo "0")
        if [ "$ERROR_COUNT" -gt 0 ]; then
            log "${YELLOW}⚠️  Se encontraron $ERROR_COUNT errores recientes${NC}"
            return 1
        else
            log "${GREEN}✅ No hay errores recientes en logs${NC}"
            return 0
        fi
    else
        log "${YELLOW}⚠️  Archivo de log no encontrado${NC}"
        return 1
    fi
}

restart_bot() {
    log "${BLUE}🔄 Reiniciando bot...${NC}"
    docker-compose restart "$BOT_NAME"
    sleep 10
    
    if check_bot_status; then
        log "${GREEN}✅ Bot reiniciado correctamente${NC}"
        return 0
    else
        log "${RED}❌ Error al reiniciar bot${NC}"
        return 1
    fi
}

send_alert() {
    local message="$1"
    log "${RED}🚨 ALERTA: $message${NC}"
    
    # Here you can add notification methods:
    # - Discord webhook
    # - Email
    # - SMS
    # - Slack
    # - etc.
    
    # Example Discord webhook (uncomment and configure):
    # if [ ! -z "$DISCORD_WEBHOOK_URL" ]; then
    #     curl -H "Content-Type: application/json" \
    #          -X POST \
    #          -d "{\"content\":\"🚨 ONZA Bot Alert: $message\"}" \
    #          "$DISCORD_WEBHOOK_URL"
    # fi
}

main() {
    log "🔍 Iniciando monitoreo del bot..."
    
    while true; do
        log "📊 Verificando estado del bot..."
        
        # Check all components
        STATUS_OK=true
        
        if ! check_bot_status; then
            STATUS_OK=false
            send_alert "Bot está detenido"
        fi
        
        if ! check_bot_health; then
            STATUS_OK=false
            send_alert "Bot no está saludable"
        fi
        
        if ! check_database; then
            STATUS_OK=false
            send_alert "Problema con base de datos"
        fi
        
        if ! check_logs; then
            STATUS_OK=false
            send_alert "Errores detectados en logs"
        fi
        
        if [ "$STATUS_OK" = true ]; then
            log "${GREEN}✅ Todas las verificaciones pasaron${NC}"
        else
            log "${YELLOW}⚠️  Algunas verificaciones fallaron${NC}"
            
            # Try to restart if bot is down
            if ! check_bot_status; then
                log "${BLUE}🔄 Intentando reiniciar bot...${NC}"
                restart_bot
            fi
        fi
        
        log "⏳ Esperando $CHECK_INTERVAL segundos para siguiente verificación..."
        sleep $CHECK_INTERVAL
    done
}

# Handle script interruption
trap 'log "🛑 Monitoreo detenido"; exit 0' INT TERM

# Start monitoring
main
