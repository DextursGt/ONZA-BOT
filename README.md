# 🤖 ONZA Bot - Discord Bot Optimizado

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/nextcord-3.1.1-green.svg)](https://github.com/nextcord/nextcord)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

Bot de Discord optimizado para gestión de tickets, tienda y soporte con arquitectura modular y soporte para hosting 24/7.

## ✨ Características

- 🎫 **Sistema de Tickets**: Creación, gestión y escalación automática
- 🛒 **Tienda Integrada**: Gestión de productos y opciones
- 🌍 **Soporte Multiidioma**: Español e Inglés
- 🔐 **Sistema de Roles**: Control de acceso granular
- 📊 **Dashboard**: Estadísticas y métricas en tiempo real
- 💳 **Pagos**: Integración con Stripe y MercadoPago (opcional)
- 🤖 **IA**: Soporte para OpenAI (opcional)
- 📦 **Entregas Automáticas**: Sistema de entrega inteligente
- 🐳 **Docker Ready**: Despliegue fácil en cualquier host
- 📱 **Hosting 24/7**: Scripts de monitoreo y auto-recuperación
- 🌐 **Keep-Alive Web**: Servidor Flask integrado para mantener el bot activo 24/7

## 🌐 Keep-Alive Web Server

El bot incluye un servidor web Flask integrado que mantiene el bot activo 24/7 en servicios gratuitos como Render, Railway, o Heroku. Esto evita que el bot se "duerma" por inactividad.

### Características del Keep-Alive:
- **🌐 Servidor Web**: Flask corriendo en puerto 8000
- **📊 Página de Estado**: Interfaz web para verificar que el bot está activo
- **🔍 Endpoints de Monitoreo**: `/status` y `/health` para servicios de monitoreo
- **⚡ Inicio Automático**: Se inicia automáticamente con el bot
- **🔄 Hilo Separado**: No interfiere con el funcionamiento del bot

### Acceso Web:
- **Página Principal**: `https://tu-bot-url.onrender.com/`
- **Estado del Bot**: `https://tu-bot-url.onrender.com/status`
- **Salud del Servicio**: `https://tu-bot-url.onrender.com/health`

## 🚀 Despliegue Rápido

### Opción 1: Docker (Recomendado)

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/onza-bot.git
cd onza-bot

# Configurar variables de entorno
cp env.example .env
nano .env  # Editar con tus valores

# Desplegar con Docker
chmod +x deploy.sh
./deploy.sh
```

### Opción 2: Hosting Tradicional

```bash
# Instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
nano .env

# Iniciar bot
python bot.py
```

### Opción 3: VPS/Dedicado

```bash
# Instalar como servicio del sistema
sudo cp onza-bot.service /etc/systemd/system/
sudo systemctl enable onza-bot
sudo systemctl start onza-bot
```

## 🔧 Configuración

### Variables de Entorno Requeridas

```env
# Discord Bot Configuration
DISCORD_TOKEN=tu_token_del_bot
GUILD_ID=id_de_tu_servidor
STAFF_ROLE_ID=id_del_rol_staff

# Opcionales
SUPPORT_ROLE_ID=id_del_rol_soporte
CLIENT_ROLE_ID=id_del_rol_cliente
OPENAI_API_KEY=tu_api_key_de_openai
STRIPE_SECRET_KEY=tu_clave_secreta_de_stripe
MP_ACCESS_TOKEN=tu_token_de_mercadopago
```

### Permisos del Bot

- **Manage Channels**: Para crear canales de tickets
- **Send Messages**: Para enviar mensajes
- **Read Message History**: Para leer historial
- **Embed Links**: Para embeds
- **Pin Messages**: Para fijar mensajes
- **Use Slash Commands**: Para comandos slash

## 📋 Comandos Disponibles

### Comandos de Usuario
- `/panel` - Abrir panel de tickets
- `/ticket` - Gestión de tickets
- `/verificar` - Verificar compras
- `/reseña` - Dejar reseñas
- `/idioma` - Cambiar idioma

### Comandos de Staff
- `/reseña_aprobar` - Aprobar reseñas
- `/ticket_vincular` - Vincular tickets con órdenes
- `/dashboard` - Ver estadísticas
- `/cliente` - Información de clientes

## 🐳 Docker

### Construir Imagen

```bash
docker build -t onza-bot .
```

### Ejecutar con Docker Compose

```bash
docker-compose up -d
```

### Ver Logs

```bash
docker-compose logs -f onza-bot
```

## 📊 Monitoreo

### Script de Monitoreo

```bash
chmod +x monitor.sh
./monitor.sh
```

### Ver Estado

```bash
# Docker
docker-compose ps

# Systemd
sudo systemctl status onza-bot

# Kubernetes
kubectl get pods -l app=onza-bot
```

## 🌐 Hosting 24/7

### Plataformas Soportadas

- ✅ **VPS/Dedicado**: Ubuntu, CentOS, Debian
- ✅ **Cloud**: AWS, GCP, Azure, DigitalOcean
- ✅ **PaaS**: Heroku, Railway, Render
- ✅ **Kubernetes**: EKS, GKE, AKS
- ✅ **Docker**: Cualquier host con Docker

### Recursos Recomendados

- **CPU**: 0.5-1.0 cores
- **RAM**: 512MB-1GB
- **Storage**: 1GB
- **Bandwidth**: 100MB/month

## 🧪 Pruebas

```bash
# Ejecutar pruebas
python test_bot.py

# Verificar sintaxis
python -m py_compile bot.py
```

## 📁 Estructura del Proyecto

```
onza-bot/
├── 🤖 bot.py                    # Bot principal
├── ⚙️ config.py                 # Configuración
├── 🛠️ utils.py                  # Utilidades
├── 🌍 i18n.py                   # Traducciones
├── 🎫 tickets.py                # Sistema de tickets
├── 🗄️ db.py                     # Base de datos de tienda
├── 🐳 Dockerfile                # Imagen Docker
├── 📦 docker-compose.yml        # Orquestación
├── 🚀 deploy.sh                 # Script de despliegue
├── 📊 monitor.sh                # Monitoreo
├── 📋 requirements.txt           # Dependencias
└── 📖 README.md                 # Documentación
```

## 🔄 Actualizaciones

```bash
# Actualizar bot
git pull origin main
docker-compose down
docker-compose up -d --build

# O reiniciar servicio
sudo systemctl restart onza-bot
```

## 🚨 Solución de Problemas

### Bot no inicia
```bash
# Verificar logs
docker-compose logs onza-bot
# o
sudo journalctl -u onza-bot -f

# Verificar variables de entorno
cat .env | grep DISCORD_TOKEN
```

### Base de datos corrupta
```bash
# Hacer backup
cp *.db backups/

# Recrear base de datos
rm *.db
python bot.py  # Se recreará automáticamente
```

### Problemas de permisos
```bash
# Verificar permisos del bot en Discord
# Asegurar que tenga todos los permisos necesarios
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

- **Issues**: [GitHub Issues](https://github.com/tu-usuario/onza-bot/issues)
- **Discord**: Servidor de soporte (si existe)
- **Documentación**: Este README y comentarios en el código

## ⭐ Agradecimientos

- [nextcord](https://github.com/nextcord/nextcord) - Framework de Discord
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Base de datos asíncrona
- [Docker](https://docker.com) - Contenedores

---

**ONZA Bot** - Versión Optimizada v2.0  
*Construido con ❤️ y Python*

[![Deploy to Docker](https://img.shields.io/badge/Deploy-Docker-blue.svg)](https://docker.com)
[![Deploy to Heroku](https://img.shields.io/badge/Deploy-Heroku-purple.svg)](https://heroku.com)
[![Deploy to Railway](https://img.shields.io/badge/Deploy-Railway-orange.svg)](https://railway.app)
# ONZA-BOT
