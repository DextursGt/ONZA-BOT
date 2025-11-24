# ⚡ Comandos Rápidos - Actualizar y Reiniciar

## 🔄 Actualizar Bot desde GitHub y Reiniciar

### En el servidor (Hostinger):
```bash
ssh root@193.43.134.31
cd /root/ONZA-BOT
git pull origin main
pip install -r requirements.txt
pm2 restart ONZA-BOT
pm2 logs ONZA-BOT --lines 50
```

### Solo reiniciar el bot (sin actualizar):
```bash
pm2 restart ONZA-BOT
```

### Ver logs del bot:
```bash
pm2 logs ONZA-BOT --lines 50
```

### Ver estado del bot:
```bash
pm2 status
```

## 📤 Subir Cambios a GitHub (desde tu PC)

```bash
cd "C:\Users\sidel\OneDrive\Desktop\ONZA\Onza-Bot\ONZA-BOT"
git add .
git commit -m "Descripción del cambio"
git push origin main
```

## 🔄 Secuencia Completa (PC → GitHub → Servidor)

### 1. En tu PC (subir cambios):
```bash
cd "C:\Users\sidel\OneDrive\Desktop\ONZA\Onza-Bot\ONZA-BOT"
git add .
git commit -m "Tu mensaje aquí"
git push origin main
```

### 2. En el servidor (actualizar y reiniciar):
```bash
ssh root@193.43.134.31
cd /root/ONZA-BOT
git pull origin main
pip install -r requirements.txt
pm2 restart ONZA-BOT
pm2 logs ONZA-BOT --lines 50
```

## 📋 Comandos Más Usados

| Acción | Comando |
|--------|---------|
| **Conectar al servidor** | `ssh root@193.43.134.31` |
| **Ir al directorio del bot** | `cd /root/ONZA-BOT` |
| **Actualizar código** | `git pull origin main` |
| **Instalar dependencias** | `pip install -r requirements.txt` |
| **Reiniciar bot** | `pm2 restart ONZA-BOT` |
| **Ver logs** | `pm2 logs ONZA-BOT --lines 50` |
| **Ver estado** | `pm2 status` |
| **Reiniciar todo (bot + n8n)** | `pm2 restart all` |

## 🚨 Si algo falla

### Forzar reinicio del bot:
```bash
pm2 delete ONZA-BOT
cd /root/ONZA-BOT
pm2 start main.py --name ONZA-BOT --interpreter python3
pm2 logs ONZA-BOT
```

### Ver errores recientes:
```bash
pm2 logs ONZA-BOT --err --lines 100
```

