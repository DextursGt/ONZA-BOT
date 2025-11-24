# 🔄 Comandos para Reiniciar el Servidor y el Bot

## 📋 Acceso al Servidor

```bash
ssh root@193.43.134.31
```

## 🔄 Reiniciar el Bot (PM2)

### Ver estado del bot:
```bash
pm2 list
```

### Reiniciar solo el bot de Discord:
```bash
pm2 restart ONZA-BOT
```

### Reiniciar todos los procesos PM2 (bot + n8n):
```bash
pm2 restart all
```

### Ver logs del bot:
```bash
pm2 logs ONZA-BOT --lines 50
```

### Ver logs en tiempo real:
```bash
pm2 logs ONZA-BOT
```

## 🔄 Reiniciar el Servidor Completo

### Reiniciar el servidor (requiere confirmación):
```bash
reboot
```

### Reiniciar el servidor inmediatamente:
```bash
reboot now
```

### Apagar el servidor:
```bash
shutdown -h now
```

## 📦 Actualizar y Reiniciar el Bot

### Secuencia completa (actualizar código + reiniciar):
```bash
# 1. Conectarse al servidor
ssh root@193.43.134.31

# 2. Ir al directorio del bot
cd /root/ONZA-BOT

# 3. Actualizar código desde GitHub
git pull origin main

# 4. Instalar dependencias si hay cambios
pip install -r requirements.txt

# 5. Reiniciar el bot
pm2 restart ONZA-BOT

# 6. Verificar que está corriendo
pm2 status
```

## 🔍 Verificar Estado

### Ver todos los procesos PM2:
```bash
pm2 status
```

### Ver información detallada del bot:
```bash
pm2 describe ONZA-BOT
```

### Ver uso de recursos:
```bash
pm2 monit
```

## ⚠️ Comandos de Emergencia

### Si el bot no responde, forzar reinicio:
```bash
pm2 delete ONZA-BOT
pm2 start main.py --name ONZA-BOT --interpreter python3
```

### Detener el bot:
```bash
pm2 stop ONZA-BOT
```

### Iniciar el bot:
```bash
pm2 start ONZA-BOT
```

### Eliminar el bot de PM2 (y luego reiniciarlo):
```bash
pm2 delete ONZA-BOT
```

## 📝 Notas Importantes

- **PM2** mantiene el bot corriendo incluso después de cerrar la sesión SSH
- **n8n** también está corriendo con PM2, usa `pm2 restart all` si necesitas reiniciar ambos
- Los logs se guardan automáticamente en PM2
- El bot se reinicia automáticamente si el servidor se reinicia (si PM2 está configurado para iniciar al boot)

## 🔐 Configurar PM2 para Inicio Automático

Si quieres que PM2 inicie automáticamente al reiniciar el servidor:

```bash
# Guardar configuración actual de PM2
pm2 save

# Configurar PM2 para iniciar al boot
pm2 startup
# (Sigue las instrucciones que aparecen)
```

