# 🔄 Actualizar Bot en Hostinger (Ya en Ejecución)

Guía para actualizar tu bot ONZA-BOT que ya está corriendo en Hostinger con el nuevo módulo de Fortnite.

## ⚡ Actualización Rápida (5 minutos)

### Paso 1: Hacer Commit y Push (Local)

```powershell
# En PowerShell, desde la carpeta del proyecto
cd C:\Users\sidel\OneDrive\Desktop\ONZA\Onza-Bot\ONZA-BOT

# Ver qué archivos cambiaron
git status

# Agregar todos los cambios
git add .

# Hacer commit
git commit -m "Agregar módulo Fortnite con seguridad anti-baneo"

# Subir a GitHub
git push origin main
```

### Paso 2: Actualizar en el Servidor

```bash
# Conectarse al servidor
ssh root@193.43.134.31

# Ir al directorio del bot (ajusta la ruta si es diferente)
cd /root/ONZA-BOT

# Ver estado actual
git status

# Actualizar código desde GitHub
git pull origin main

# Instalar nuevas dependencias (cryptography para Fortnite)
source venv/bin/activate  # Si usas entorno virtual
pip install -r requirements.txt

# Reiniciar el bot para cargar los cambios
systemctl restart onza-bot

# Verificar que inició correctamente
systemctl status onza-bot
```

### Paso 3: Verificar que Funciona

```bash
# Ver logs en tiempo real
journalctl -u onza-bot -f
```

**Busca estas líneas en los logs:**
- ✅ `"Cog de Fortnite inicializado"`
- ✅ `"Módulo de Fortnite cargado"`
- ✅ `"Bot integrado completamente operativo"`
- ❌ **NO deberías ver errores** relacionados con `fortnite` o `cryptography`

## 🔍 Verificación Detallada

### Verificar que el Módulo se Cargó

```bash
# Ver los últimos logs
journalctl -u onza-bot -n 100 | grep -i fortnite
```

Deberías ver algo como:
```
INFO - Cog de Fortnite inicializado
INFO - Módulo de Fortnite cargado
```

### Probar Comandos en Discord

1. **Comando básico**: `/help` (debería funcionar)
2. **Comando Fortnite**: `/fn_list_accounts` (debería decir que no hay cuentas, NO debería dar error de comando no encontrado)

## ⚠️ Si Algo Sale Mal

### Error: "ModuleNotFoundError: No module named 'cryptography'"

```bash
# Instalar dependencia faltante
source venv/bin/activate
pip install cryptography==41.0.7
systemctl restart onza-bot
```

### Error: "No module named 'fortnite'"

```bash
# Verificar que la carpeta fortnite existe
ls -la /root/ONZA-BOT/fortnite/

# Si no existe, hacer pull nuevamente
cd /root/ONZA-BOT
git pull origin main
```

### El Bot No Inicia

```bash
# Ver errores detallados
journalctl -u onza-bot -n 50 --no-pager

# Verificar que Python puede importar el módulo
cd /root/ONZA-BOT
source venv/bin/activate
python -c "from fortnite.fortnite_cog import FortniteCommands; print('OK')"
```

### El Bot se Desconecta

```bash
# Ver logs en tiempo real para detectar el error
journalctl -u onza-bot -f

# Si hay un error específico, compártelo para solucionarlo
```

## 🔄 Rollback (Volver a Versión Anterior)

Si algo sale mal y necesitas volver atrás:

```bash
# En el servidor
cd /root/ONZA-BOT

# Ver commits recientes
git log --oneline -5

# Volver al commit anterior
git reset --hard HEAD~1

# O volver a un commit específico
git reset --hard <commit-hash>

# Reiniciar bot
systemctl restart onza-bot
```

## 📋 Checklist de Actualización

- [ ] Código actualizado en GitHub (`git push`)
- [ ] Código actualizado en servidor (`git pull`)
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Bot reiniciado (`systemctl restart onza-bot`)
- [ ] Logs verificados (sin errores)
- [ ] Comandos probados en Discord

## 🎯 Comandos en Una Línea (Copy-Paste)

```bash
# Todo el proceso de actualización:
ssh root@193.43.134.31 "cd /root/ONZA-BOT && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && systemctl restart onza-bot && systemctl status onza-bot"
```

## 💡 Tips

1. **Haz backup antes de actualizar** (opcional pero recomendado):
   ```bash
   cd /root/ONZA-BOT
   cp -r . ../ONZA-BOT-backup-$(date +%Y%m%d)
   ```

2. **Mantén el bot actualizado regularmente**:
   ```bash
   # Crear alias útil
   alias update-bot='cd /root/ONZA-BOT && git pull && source venv/bin/activate && pip install -r requirements.txt && systemctl restart onza-bot'
   ```

3. **Monitorea los logs después de actualizar**:
   ```bash
   # Ver logs durante los primeros minutos
   journalctl -u onza-bot -f
   ```

---

**¡Listo!** Tu bot debería estar actualizado con el módulo de Fortnite. 🎮

