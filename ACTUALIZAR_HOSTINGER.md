# 🚀 Comandos para Actualizar Bot en Hostinger

Guía rápida con comandos copy-paste para actualizar el bot en tu servidor Hostinger.

## 📋 Comandos Rápidos (Copy-Paste)

### Opción 1: Actualización Completa (Recomendado)

```bash
# Conectarse al servidor
ssh root@193.43.134.31

# Ir al directorio del bot
cd /root/ONZA-BOT

# Resolver conflicto si existe (guardar cambios locales)
git stash

# Actualizar desde GitHub
git pull origin main

# Instalar nuevas dependencias
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Reiniciar con PM2
pm2 restart ONZA-BOT

# Ver logs
pm2 logs ONZA-BOT
```

### Opción 2: Solo Módulo Fortnite (Sin Tocar Archivos Principales)

```bash
# Conectarse
ssh root@193.43.134.31

# Ir al directorio
cd /root/ONZA-BOT

# Actualizar solo carpeta fortnite/
git fetch origin
git checkout origin/main -- fortnite/

# Agregar cryptography si no existe
grep -q "cryptography" requirements.txt || echo -e "\n# Encryption for Fortnite tokens\ncryptography==41.0.7" >> requirements.txt

# Instalar dependencia
source venv/bin/activate
pip install cryptography==41.0.7
deactivate

# Editar main.py manualmente (agregar código de Fortnite si no existe)
nano main.py
# Busca: self.add_cog(SimpleTicketCommands(self))
# Agrega después:
#            # Cargar módulo de Fortnite
#            try:
#                from fortnite.fortnite_cog import FortniteCommands
#                self.add_cog(FortniteCommands(self))
#                log.info("✅ Módulo de Fortnite cargado")
#            except Exception as e:
#                log.warning(f"⚠️ Error cargando módulo de Fortnite: {e}")

# Reiniciar
pm2 restart ONZA-BOT

# Ver logs
pm2 logs ONZA-BOT
```

### Opción 3: Usar Script Automático

```bash
# Conectarse
ssh root@193.43.134.31

# Ir al directorio
cd /root/ONZA-BOT

# Resolver conflicto
git stash

# Actualizar código
git pull origin main

# Ejecutar script
bash actualizar_fortnite.sh

# Reiniciar
pm2 restart ONZA-BOT

# Ver logs
pm2 logs ONZA-BOT
```

## 🔍 Verificar Estado del Bot

```bash
# Ver procesos PM2
pm2 list

# Ver estado específico
pm2 status ONZA-BOT

# Ver logs en tiempo real
pm2 logs ONZA-BOT

# Ver últimos logs
pm2 logs ONZA-BOT --lines 50
```

## 🆘 Si Hay Problemas

### Error: Conflicto de Git

```bash
cd /root/ONZA-BOT
git stash  # Guardar cambios locales
git pull origin main
```

### Error: Servicio no encontrado

```bash
# Ver procesos PM2
pm2 list

# Si no está en PM2, buscar proceso
ps aux | grep "python.*main.py"

# Reiniciar manualmente si es necesario
cd /root/ONZA-BOT
source venv/bin/activate
python main.py
```

### Error: Dependencias faltantes

```bash
cd /root/ONZA-BOT
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## ✅ Verificar que Funciona

Después de actualizar, busca en los logs:

```bash
pm2 logs ONZA-BOT | grep -i "fortnite\|operativo\|error"
```

Deberías ver:
- ✅ `"Módulo de Fortnite cargado"`
- ✅ `"Bot integrado completamente operativo"`
- ❌ **NO deberías ver errores** relacionados con Fortnite

## 📝 Todo en Un Comando

```bash
ssh root@193.43.134.31 "cd /root/ONZA-BOT && git stash && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && deactivate && pm2 restart ONZA-BOT && echo '✅ Actualización completada'"
```

---

**¡Listo!** Copia y pega los comandos según tu necesidad. 🚀

