# ⚡ Despliegue Rápido a Hostinger

## 🚀 Método Rápido (Recomendado)

### Opción 1: Usar Git (Más Fácil)

```bash
# 1. En tu máquina local - hacer commit y push
cd ONZA-BOT
git add .
git commit -m "Actualizar bot con módulo Fortnite"
git push origin main

# 2. Conectarse al servidor y actualizar
ssh root@193.43.134.31
cd /root/ONZA-BOT
git pull origin main

# 3. Instalar dependencias si hay cambios
source venv/bin/activate
pip install -r requirements.txt

# 4. Reiniciar el bot
systemctl restart onza-bot
```

### Opción 2: Usar SCP (Transferencia Directa)

Desde PowerShell en Windows:

```powershell
# Navegar al proyecto
cd C:\Users\sidel\OneDrive\Desktop\ONZA\Onza-Bot\ONZA-BOT

# Subir archivos (excluyendo venv, .git, etc.)
scp -r fortnite/ commands/ events/ views/ *.py requirements.txt root@193.43.134.31:/root/ONZA-BOT/
```

Luego en el servidor:

```bash
ssh root@193.43.134.31
cd /root/ONZA-BOT
source venv/bin/activate
pip install -r requirements.txt
systemctl restart onza-bot
```

## 📋 Checklist Rápido

1. ✅ Código subido al servidor
2. ✅ Dependencias instaladas (`pip install -r requirements.txt`)
3. ✅ Archivo `.env` configurado (si no existe, créalo)
4. ✅ Bot reiniciado (`systemctl restart onza-bot`)

## 🔍 Verificar que Funciona

```bash
# Ver logs en tiempo real
ssh root@193.43.134.31
journalctl -u onza-bot -f
```

Deberías ver:
- ✅ "Cog de Fortnite inicializado"
- ✅ "Bot integrado completamente operativo"
- ✅ Sin errores relacionados con Fortnite

## ⚠️ Si Algo Sale Mal

```bash
# Ver errores recientes
journalctl -u onza-bot -n 50

# Verificar que Python puede importar el módulo
cd /root/ONZA-BOT
source venv/bin/activate
python -c "from fortnite.fortnite_cog import FortniteCommands; print('OK')"
```

---

**Ver guía completa**: `DEPLOY_HOSTINGER.md`

