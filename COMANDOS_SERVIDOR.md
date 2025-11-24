# 🖥️ Comandos para Ejecutar en el Servidor (SSH)

Guía completa con todos los comandos para actualizar solo Fortnite directamente desde la terminal del servidor.

## 🔐 Paso 1: Conectarse al Servidor

```bash
ssh root@193.43.134.31
```

## 💾 Paso 2: Hacer Backup (MUY IMPORTANTE)

```bash
cd /root/ONZA-BOT
cp -r . ../ONZA-BOT-backup-$(date +%Y%m%d-%H%M%S)
echo "✅ Backup creado en: ../ONZA-BOT-backup-$(date +%Y%m%d-%H%M%S)"
```

## 📥 Paso 3: Actualizar Solo la Carpeta Fortnite desde GitHub

```bash
cd /root/ONZA-BOT

# Ver estado actual
git status

# Descargar cambios desde GitHub (sin aplicar todavía)
git fetch origin

# Ver qué archivos cambiaron
git diff HEAD origin/main --name-only

# Actualizar SOLO la carpeta fortnite/
git checkout origin/main -- fortnite/

# Verificar que se actualizó
ls -la fortnite/
```

## 📝 Paso 4: Actualizar main.py (Agregar Líneas de Fortnite)

```bash
cd /root/ONZA-BOT

# Ver el contenido actual de main.py alrededor de donde necesitamos agregar código
grep -n "SimpleTicketCommands" main.py

# Editar main.py
nano main.py
```

**En nano, busca la línea que dice:**
```python
self.add_cog(SimpleTicketCommands(self))
```

**Agrega DESPUÉS de esa línea (antes de "# Registrar vistas persistentes"):**

```python
            # Cargar módulo de Fortnite
            try:
                from fortnite.fortnite_cog import FortniteCommands
                self.add_cog(FortniteCommands(self))
                log.info("✅ Módulo de Fortnite cargado")
            except Exception as e:
                log.warning(f"⚠️ Error cargando módulo de Fortnite: {e}")
```

**Guardar**: `Ctrl+X`, luego `Y`, luego `Enter`

## 📦 Paso 5: Actualizar requirements.txt

```bash
cd /root/ONZA-BOT

# Verificar si cryptography ya existe
grep -q "cryptography" requirements.txt && echo "✅ cryptography ya existe" || echo "❌ cryptography no existe"

# Agregar cryptography si no existe
if ! grep -q "cryptography" requirements.txt; then
    echo "" >> requirements.txt
    echo "# Encryption for Fortnite tokens" >> requirements.txt
    echo "cryptography==41.0.7" >> requirements.txt
    echo "✅ cryptography agregado a requirements.txt"
else
    echo "✅ cryptography ya está en requirements.txt"
fi

# Verificar
tail -3 requirements.txt
```

## 🔧 Paso 6: Instalar Nueva Dependencia

```bash
cd /root/ONZA-BOT

# Activar entorno virtual
source venv/bin/activate

# Instalar cryptography
pip install cryptography==41.0.7

# Verificar que se instaló
pip list | grep cryptography

# Salir del entorno virtual (opcional)
deactivate
```

## 🚀 Paso 7: Reiniciar el Bot

```bash
# Si usas systemd
systemctl restart onza-bot

# Ver estado
systemctl status onza-bot

# Ver logs en tiempo real
journalctl -u onza-bot -f
```

**Busca en los logs:**
- ✅ `"Módulo de Fortnite cargado"`
- ✅ `"Cog de Fortnite inicializado"`
- ✅ `"Bot integrado completamente operativo"`

## 📋 Script Completo (Copy-Paste Todo Junto)

```bash
#!/bin/bash
# Ejecutar todo el proceso de actualización

cd /root/ONZA-BOT

# 1. Backup
echo "💾 Creando backup..."
cp -r . ../ONZA-BOT-backup-$(date +%Y%m%d-%H%M%S)
echo "✅ Backup creado"

# 2. Actualizar fortnite desde GitHub
echo "📥 Actualizando carpeta fortnite/..."
git fetch origin
git checkout origin/main -- fortnite/
echo "✅ Carpeta fortnite/ actualizada"

# 3. Verificar si main.py necesita actualización
echo "📝 Verificando main.py..."
if ! grep -q "fortnite.fortnite_cog" main.py; then
    echo "⚠️  Necesitas editar main.py manualmente"
    echo "   Busca: self.add_cog(SimpleTicketCommands(self))"
    echo "   Agrega después:"
    echo "   # Cargar módulo de Fortnite"
    echo "   try:"
    echo "       from fortnite.fortnite_cog import FortniteCommands"
    echo "       self.add_cog(FortniteCommands(self))"
    echo "       log.info(\"✅ Módulo de Fortnite cargado\")"
    echo "   except Exception as e:"
    echo "       log.warning(f\"⚠️ Error cargando módulo de Fortnite: {e}\")"
else
    echo "✅ main.py ya tiene el código de Fortnite"
fi

# 4. Actualizar requirements.txt
echo "📦 Actualizando requirements.txt..."
if ! grep -q "cryptography" requirements.txt; then
    echo "" >> requirements.txt
    echo "# Encryption for Fortnite tokens" >> requirements.txt
    echo "cryptography==41.0.7" >> requirements.txt
    echo "✅ cryptography agregado"
else
    echo "✅ cryptography ya existe"
fi

# 5. Instalar dependencia
echo "🔧 Instalando cryptography..."
source venv/bin/activate
pip install -q cryptography==41.0.7
deactivate
echo "✅ cryptography instalado"

# 6. Reiniciar bot
echo "🚀 Reiniciando bot..."
systemctl restart onza-bot
sleep 2
systemctl status onza-bot --no-pager -l | head -20

echo ""
echo "✅ Proceso completado!"
echo "📊 Ver logs: journalctl -u onza-bot -f"
```

## 🔍 Verificar Cambios Antes de Aplicar

Si quieres ver qué va a cambiar antes de aplicarlo:

```bash
cd /root/ONZA-BOT

# Ver diferencias en fortnite/
git fetch origin
git diff HEAD origin/main -- fortnite/ | head -50

# Ver diferencias en main.py
git diff HEAD origin/main -- main.py

# Ver diferencias en requirements.txt
git diff HEAD origin/main -- requirements.txt
```

## 🆘 Si Algo Sale Mal - Rollback

```bash
cd /root/ONZA-BOT

# Eliminar carpeta fortnite
rm -rf fortnite/

# Restaurar desde backup (reemplaza la fecha)
# cp ../ONZA-BOT-backup-YYYYMMDD-HHMMSS/fortnite/ ./ -r

# O restaurar todo desde backup
# cp -r ../ONZA-BOT-backup-YYYYMMDD-HHMMSS/* .

# Reiniciar
systemctl restart onza-bot
```

## ✅ Verificación Final

```bash
# Verificar que fortnite existe
ls -la /root/ONZA-BOT/fortnite/

# Verificar que main.py tiene el código
grep -A 5 "fortnite.fortnite_cog" /root/ONZA-BOT/main.py

# Verificar que cryptography está instalado
source /root/ONZA-BOT/venv/bin/activate
pip list | grep cryptography
deactivate

# Ver logs del bot
journalctl -u onza-bot -n 50 | grep -i fortnite
```

## 📝 Editar main.py con sed (Automático)

Si prefieres hacerlo automáticamente sin nano:

```bash
cd /root/ONZA-BOT

# Verificar si ya tiene el código
if ! grep -q "fortnite.fortnite_cog" main.py; then
    # Crear backup de main.py
    cp main.py main.py.backup
    
    # Agregar código después de SimpleTicketCommands
    sed -i '/self.add_cog(SimpleTicketCommands(self))/a\
            # Cargar módulo de Fortnite\
            try:\
                from fortnite.fortnite_cog import FortniteCommands\
                self.add_cog(FortniteCommands(self))\
                log.info("✅ Módulo de Fortnite cargado")\
            except Exception as e:\
                log.warning(f"⚠️ Error cargando módulo de Fortnite: {e}")' main.py
    
    echo "✅ main.py actualizado automáticamente"
else
    echo "✅ main.py ya tiene el código de Fortnite"
fi
```

---

**¡Todo listo! Copia y pega los comandos en tu terminal SSH.** 🚀

