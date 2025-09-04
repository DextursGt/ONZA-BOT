#!/bin/bash

# Script simple para ejecutar ONZA Bot
echo "🚀 ONZA Bot - Ejecución Directa"
echo "================================"

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
source .venv/bin/activate

# Verificar dependencias
echo "🔍 Verificando dependencias..."
python -c "import nextcord, aiosqlite; print('✅ Dependencias OK')" || {
    echo "❌ Error: Faltan dependencias"
    exit 1
}

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Error: Archivo .env no encontrado"
    echo "📝 Copia env.example a .env y configura tus variables"
    exit 1
fi

echo "✅ Configuración verificada"
echo ""
echo "🤖 Iniciando ONZA Bot..."
echo "💡 Presiona Ctrl+C para detener"
echo ""

# Ejecutar bot directamente
python bot.py
