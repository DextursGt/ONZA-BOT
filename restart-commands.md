# 🔄 Comandos para Reiniciar el Hosting - ONZA Bot

## Hostinger VPS

### Reinicio Rápido del Bot
```bash
sudo systemctl restart onza-bot
sudo systemctl status onza-bot
```

### Reinicio Completo del VPS
```bash
sudo reboot
# Esperar 2-3 minutos, luego verificar:
sudo systemctl status onza-bot
```

### Monitoreo
```bash
# Ver logs en tiempo real
sudo journalctl -u onza-bot -f

# Ver estado actual
sudo systemctl status onza-bot

# Script de monitoreo
./monitor-systemd.sh
```

## Render.com

### Desde Dashboard
1. Ir a dashboard.render.com
2. Buscar servicio "onza-bot"
3. Clic en "Manual Deploy" → "Deploy latest commit"

### Desde CLI
```bash
render services restart onza-bot
```

## Comandos de Emergencia

### Si el bot no responde
```bash
# Matar procesos
pkill -f "python.*main.py"

# Reiniciar servicio
sudo systemctl restart onza-bot

# Verificar
sudo systemctl status onza-bot
```

### Verificar conectividad
```bash
# Ping a Discord
ping discord.com

# Ver logs de errores
tail -f logs/onza_bot.log
```

## Checklist Post-Reinicio

- [ ] `sudo systemctl status onza-bot` - Estado OK
- [ ] `sudo journalctl -u onza-bot --since "5 minutes ago"` - Sin errores
- [ ] Probar `/help` en Discord - Bot responde
- [ ] `ls -la data/` - Base de datos existe

## Solución de Problemas

### Bot no se conecta
```bash
# Verificar token
grep DISCORD_TOKEN .env

# Verificar permisos
sudo chown -R $USER:$USER /ruta/a/onza-bot
```

### Base de datos corrupta
```bash
# Restaurar backup
cp backups/backup_YYYYMMDD_HHMMSS.db data/onza_bot.db
sudo systemctl restart onza-bot
```

---
**Fecha de creación:** $(date)
**Última actualización:** $(date)
