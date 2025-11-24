# 🔄 Reiniciar Servicios en Hostinger

## 🔍 Encontrar el Servicio

Ejecuta estos comandos en el servidor para encontrar el servicio:

```bash
# Ver todos los servicios activos
systemctl list-units --type=service --state=running | grep -E "n8n|discord|bot|onza"

# Ver todos los servicios (activos e inactivos)
systemctl list-units --type=service --all | grep -E "n8n|discord|bot|onza"

# Buscar servicios que contengan "n8n"
systemctl list-units --all | grep n8n

# Ver procesos corriendo
ps aux | grep -E "n8n|python.*main.py|node.*n8n"

# Ver servicios systemd relacionados
systemctl list-unit-files | grep -E "n8n|discord|bot"
```

## 📋 Nombres Comunes de Servicios

Los servicios suelen llamarse:
- `n8n.service`
- `discord-bot.service`
- `onza-bot.service`
- `bot.service`
- `n8n-bot.service`
- `apps.service` (si ejecuta múltiples apps)

## 🔄 Reiniciar el Servicio

Una vez que encuentres el nombre:

```bash
# Reiniciar
systemctl restart NOMBRE_DEL_SERVICIO

# Ver estado
systemctl status NOMBRE_DEL_SERVICIO

# Ver logs
journalctl -u NOMBRE_DEL_SERVICIO -f
```

## 🔍 Buscar en Archivos de Configuración

Si no encuentras el servicio, busca en los archivos de configuración:

```bash
# Buscar archivos de servicio
ls -la /etc/systemd/system/ | grep -E "n8n|bot|discord"

# Ver contenido de servicios
cat /etc/systemd/system/*.service | grep -A 10 -B 5 -E "n8n|main.py"

# Buscar scripts de inicio
find /root -name "*.sh" -o -name "start*" -o -name "run*" | xargs grep -l "n8n\|main.py"
```

## 🚀 Si Usa PM2 (Process Manager)

Si usa PM2 para Node.js:

```bash
# Ver procesos
pm2 list

# Reiniciar todo
pm2 restart all

# Reiniciar específico
pm2 restart n8n
pm2 restart discord-bot

# Ver logs
pm2 logs
```

## 🐳 Si Usa Docker

Si usa Docker:

```bash
# Ver contenedores
docker ps

# Reiniciar contenedor
docker restart NOMBRE_CONTENEDOR

# Ver logs
docker logs -f NOMBRE_CONTENEDOR
```

## 📝 Si Usa Screen o Tmux

Si ejecuta en screen/tmux:

```bash
# Ver screens
screen -ls

# Ver tmux
tmux ls

# Entrar a screen
screen -r NOMBRE_SCREEN

# Reiniciar: Ctrl+C para detener, luego ejecutar de nuevo
```

## 🔧 Script para Encontrar y Reiniciar

Ejecuta este script para encontrar automáticamente:

```bash
#!/bin/bash

echo "🔍 Buscando servicios..."

# Buscar en systemd
SERVICES=$(systemctl list-units --all --type=service | grep -E "n8n|discord|bot|onza" | awk '{print $1}')

if [ -n "$SERVICES" ]; then
    echo "✅ Servicios encontrados:"
    echo "$SERVICES"
    echo ""
    read -p "¿Reiniciar todos? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        for service in $SERVICES; do
            echo "🔄 Reiniciando $service..."
            systemctl restart $service
            systemctl status $service --no-pager | head -5
        done
    fi
else
    echo "❌ No se encontraron servicios systemd"
    echo ""
    echo "🔍 Buscando procesos..."
    ps aux | grep -E "n8n|python.*main.py" | grep -v grep
fi
```

## 💡 Comandos Rápidos

```bash
# Ver todos los servicios
systemctl list-units --type=service

# Reiniciar servicio específico (reemplaza NOMBRE)
systemctl restart NOMBRE

# Ver logs en tiempo real
journalctl -u NOMBRE -f

# Ver estado
systemctl status NOMBRE
```

