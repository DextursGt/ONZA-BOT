#!/bin/bash

# Script para actualizar solo Fortnite en el servidor
# Uso: bash actualizar_fortnite.sh

set -e  # Salir si hay error

echo "🎮 Actualizando módulo Fortnite en ONZA-BOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /root/ONZA-BOT

# 1. Backup
echo "💾 Paso 1: Creando backup..."
BACKUP_DIR="../ONZA-BOT-backup-$(date +%Y%m%d-%H%M%S)"
cp -r . "$BACKUP_DIR"
echo "✅ Backup creado en: $BACKUP_DIR"
echo ""

# 2. Actualizar fortnite desde GitHub
echo "📥 Paso 2: Actualizando carpeta fortnite/ desde GitHub..."
git fetch origin

# Verificar si hay cambios en fortnite
if git diff --quiet HEAD origin/main -- fortnite/; then
    echo "ℹ️  No hay cambios en fortnite/"
else
    echo "📝 Cambios encontrados en fortnite/, actualizando..."
    git checkout origin/main -- fortnite/
    echo "✅ Carpeta fortnite/ actualizada"
fi
echo ""

# 3. Verificar/Actualizar main.py
echo "📝 Paso 3: Verificando main.py..."
if grep -q "fortnite.fortnite_cog" main.py; then
    echo "✅ main.py ya tiene el código de Fortnite"
else
    echo "⚠️  main.py necesita ser actualizado"
    echo ""
    echo "📋 INSTRUCCIONES:"
    echo "   1. Ejecuta: nano main.py"
    echo "   2. Busca: self.add_cog(SimpleTicketCommands(self))"
    echo "   3. Agrega DESPUÉS de esa línea:"
    echo ""
    echo "            # Cargar módulo de Fortnite"
    echo "            try:"
    echo "                from fortnite.fortnite_cog import FortniteCommands"
    echo "                self.add_cog(FortniteCommands(self))"
    echo "                log.info(\"✅ Módulo de Fortnite cargado\")"
    echo "            except Exception as e:"
    echo "                log.warning(f\"⚠️ Error cargando módulo de Fortnite: {e}\")"
    echo ""
    read -p "¿Quieres que lo agregue automáticamente? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Crear backup de main.py
        cp main.py main.py.backup
        
        # Agregar código automáticamente
        python3 << 'PYTHON_SCRIPT'
import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la línea y agregar después
pattern = r'(self\.add_cog\(SimpleTicketCommands\(self\)\))'
replacement = r'''\1
            
            # Cargar módulo de Fortnite
            try:
                from fortnite.fortnite_cog import FortniteCommands
                self.add_cog(FortniteCommands(self))
                log.info("✅ Módulo de Fortnite cargado")
            except Exception as e:
                log.warning(f"⚠️ Error cargando módulo de Fortnite: {e}")'''

if 'fortnite.fortnite_cog' not in content:
    new_content = re.sub(pattern, replacement, content)
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ main.py actualizado automáticamente")
else:
    print("✅ main.py ya tiene el código")
PYTHON_SCRIPT
        echo "✅ main.py actualizado"
    else
        echo "⚠️  Debes editar main.py manualmente antes de continuar"
    fi
fi
echo ""

# 4. Actualizar requirements.txt
echo "📦 Paso 4: Actualizando requirements.txt..."
if grep -q "cryptography" requirements.txt; then
    echo "✅ cryptography ya existe en requirements.txt"
else
    echo "" >> requirements.txt
    echo "# Encryption for Fortnite tokens" >> requirements.txt
    echo "cryptography==41.0.7" >> requirements.txt
    echo "✅ cryptography agregado a requirements.txt"
fi
echo ""

# 5. Instalar dependencia
echo "🔧 Paso 5: Instalando cryptography..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -q cryptography==41.0.7
    deactivate
    echo "✅ cryptography instalado en venv"
else
    pip3 install -q cryptography==41.0.7
    echo "✅ cryptography instalado globalmente"
fi
echo ""

# 6. Verificar instalación
echo "🔍 Paso 6: Verificando instalación..."
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 -c "import cryptography; print('✅ cryptography importado correctamente')" 2>/dev/null || echo "❌ Error importando cryptography"
    deactivate
else
    python3 -c "import cryptography; print('✅ cryptography importado correctamente')" 2>/dev/null || echo "❌ Error importando cryptography"
fi
echo ""

# 7. Verificar estructura
echo "📁 Paso 7: Verificando estructura de archivos..."
if [ -d "fortnite" ] && [ -f "fortnite/fortnite_cog.py" ]; then
    echo "✅ Carpeta fortnite/ existe y tiene archivos"
    ls -1 fortnite/*.py | wc -l | xargs echo "   Archivos Python en fortnite/:"
else
    echo "❌ ERROR: Carpeta fortnite/ no existe o está incompleta"
    exit 1
fi
echo ""

# 8. Resumen
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Actualización completada!"
echo ""
echo "📋 Resumen:"
echo "   ✅ Backup creado: $BACKUP_DIR"
echo "   ✅ Carpeta fortnite/ actualizada"
if grep -q "fortnite.fortnite_cog" main.py; then
    echo "   ✅ main.py tiene código de Fortnite"
else
    echo "   ⚠️  main.py necesita edición manual"
fi
echo "   ✅ requirements.txt actualizado"
echo "   ✅ cryptography instalado"
echo ""
echo "🚀 Próximo paso: Reiniciar el bot"
echo "   systemctl restart onza-bot"
echo "   journalctl -u onza-bot -f"
echo ""

