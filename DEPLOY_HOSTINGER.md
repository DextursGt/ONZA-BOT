# 🚀 Guía de Despliegue a Hostinger VPS

Esta guía te ayudará a subir y configurar ONZA-BOT en tu servidor Hostinger.

## 📋 Prerequisitos

- Acceso SSH a tu servidor: `root@193.43.134.31`
- Python 3.11+ instalado en el servidor
- Git instalado en el servidor

## 🔧 Paso 1: Preparar el Código Localmente

### 1.1 Hacer Commit de los Cambios

```bash
# Desde la carpeta ONZA-BOT
cd ONZA-BOT

# Agregar todos los cambios
git add .

# Hacer commit
git commit -m "Agregar módulo Fortnite con medidas de seguridad anti-baneo"

# Subir a GitHub (si usas GitHub)
git push origin main
```

## 📤 Paso 2: Subir Código al Servidor

### Opción A: Usar Git (Recomendado)

Si tu repositorio está en GitHub:

```bash
# Conectarse al servidor
ssh root@193.43.134.31

# Navegar al directorio donde está el bot (o crear uno nuevo)
cd /root  # o donde tengas el bot
cd ONZA-BOT  # o el nombre de tu directorio

# Si ya existe el repositorio, actualizar:
git pull origin main

# Si no existe, clonar:
git clone https://github.com/DextursGt/ONZA-BOT.git
cd ONZA-BOT
```

### Opción B: Usar SCP (Transferencia Directa)

Desde tu máquina local (Windows PowerShell):

```powershell
# Navegar a la carpeta del proyecto
cd C:\Users\sidel\OneDrive\Desktop\ONZA\Onza-Bot\ONZA-BOT

# Subir todo el proyecto (excluyendo archivos ignorados)
scp -r * root@193.43.134.31:/root/ONZA-BOT/

# O si prefieres subir todo incluyendo .git
scp -r . root@193.43.134.31:/root/ONZA-BOT/
```

**Nota**: SCP puede tardar si hay muchos archivos. Git es más eficiente.

## 🔐 Paso 3: Configurar Variables de Entorno

En el servidor:

```bash
# Conectarse al servidor
ssh root@193.43.134.31

# Navegar al directorio del bot
cd /root/ONZA-BOT  # o donde esté tu bot

# Crear archivo .env si no existe
nano .env
```

Agregar estas variables (ajusta los valores):

```env
# Discord Bot
DISCORD_TOKEN=tu_token_del_bot_discord
GUILD_ID=id_de_tu_servidor
BRAND_NAME=ONZA Bot

# Roles
OWNER_ROLE_ID=id_del_rol_owner
STAFF_ROLE_ID=id_del_rol_staff
SUPPORT_ROLE_ID=id_del_rol_support

# Canales
TICKET_CHANNEL_ID=id_del_canal_tickets
TICKETS_LOG_CHANNEL_ID=id_del_canal_logs

# Opcional: Clave de cifrado Fortnite (recomendado)
FORTNITE_ENCRYPTION_KEY=tu_clave_generada_con_fernet
```

Guardar con `Ctrl+X`, luego `Y`, luego `Enter`.

## 📦 Paso 4: Instalar Dependencias

En el servidor:

```bash
# Asegurarse de estar en el directorio del bot
cd /root/ONZA-BOT

# Crear entorno virtual (recomendado)
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

## 🚀 Paso 5: Configurar como Servicio Systemd (Opcional pero Recomendado)

Esto permite que el bot se ejecute automáticamente al reiniciar el servidor.

```bash
# Crear archivo de servicio
nano /etc/systemd/system/onza-bot.service
```

Agregar este contenido:

```ini
[Unit]
Description=ONZA Discord Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ONZA-BOT
Environment="PATH=/root/ONZA-BOT/venv/bin"
ExecStart=/root/ONZA-BOT/venv/bin/python /root/ONZA-BOT/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Ajusta las rutas** según donde esté tu bot.

Luego:

```bash
# Recargar systemd
systemctl daemon-reload

# Habilitar servicio (inicia automáticamente al reiniciar)
systemctl enable onza-bot

# Iniciar servicio
systemctl start onza-bot

# Ver estado
systemctl status onza-bot

# Ver logs en tiempo real
journalctl -u onza-bot -f
```

## 🧪 Paso 6: Probar el Bot

### Opción A: Ejecutar Manualmente (Para Pruebas)

```bash
# Activar entorno virtual
cd /root/ONZA-BOT
source venv/bin/activate

# Ejecutar bot
python main.py
```

### Opción B: Usar el Servicio Systemd

```bash
# Ver logs
journalctl -u onza-bot -f

# Reiniciar si es necesario
systemctl restart onza-bot
```

## 📝 Paso 7: Verificar que Funciona

1. **Verificar que el bot está en línea** en Discord
2. **Probar un comando básico**: `/help`
3. **Verificar módulo Fortnite**: `/fn_list_accounts` (debería decir que no hay cuentas)

## 🔄 Actualizar el Bot en el Futuro

Cuando hagas cambios:

```bash
# En tu máquina local
cd ONZA-BOT
git add .
git commit -m "Descripción de cambios"
git push origin main

# En el servidor
ssh root@193.43.134.31
cd /root/ONZA-BOT
git pull origin main

# Reiniciar el servicio
systemctl restart onza-bot

# O si ejecutas manualmente, detener (Ctrl+C) y volver a ejecutar
```

## 🛠️ Comandos Útiles

### Ver Logs del Bot

```bash
# Si usas systemd
journalctl -u onza-bot -f

# Si ejecutas manualmente, los logs están en:
tail -f /root/ONZA-BOT/onza_bot.log
```

### Detener el Bot

```bash
# Si usas systemd
systemctl stop onza-bot

# Si ejecutas manualmente
# Presiona Ctrl+C en la terminal
```

### Reiniciar el Bot

```bash
systemctl restart onza-bot
```

### Ver Estado del Bot

```bash
systemctl status onza-bot
```

## ⚠️ Solución de Problemas

### El bot no inicia

```bash
# Ver logs de error
journalctl -u onza-bot -n 50

# Verificar que Python está instalado
python3 --version

# Verificar que las dependencias están instaladas
source venv/bin/activate
pip list

# Verificar que el archivo .env existe y tiene las variables correctas
cat .env
```

### Error de permisos

```bash
# Dar permisos de ejecución
chmod +x main.py

# Verificar permisos del directorio
ls -la
```

### Error de dependencias

```bash
# Reinstalar dependencias
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### El bot se desconecta frecuentemente

```bash
# Verificar conexión a internet
ping google.com

# Verificar que el token de Discord es válido
# Revisar logs para ver errores específicos
journalctl -u onza-bot -f
```

## 📁 Estructura de Directorios Recomendada

```
/root/
└── ONZA-BOT/
    ├── main.py
    ├── config.py
    ├── requirements.txt
    ├── .env                    # Variables de entorno (NO subir a git)
    ├── .fortnite_key          # Clave de cifrado (NO subir a git)
    ├── data/                  # Datos del bot
    ├── fortnite/              # Módulo Fortnite
    ├── commands/              # Comandos del bot
    ├── events/                # Eventos del bot
    ├── views/                 # Vistas del bot
    ├── venv/                  # Entorno virtual
    └── onza_bot.log           # Logs del bot
```

## 🔒 Seguridad

1. **Nunca subas el archivo `.env` a git** (ya está en .gitignore)
2. **Nunca subas `.fortnite_key`** (ya está en .gitignore)
3. **Usa permisos restrictivos**:
   ```bash
   chmod 600 .env
   chmod 600 .fortnite_key
   ```
4. **Mantén el bot actualizado** con las últimas versiones de dependencias

## ✅ Checklist de Despliegue

- [ ] Código subido al servidor
- [ ] Archivo `.env` configurado con todas las variables
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Bot probado manualmente
- [ ] Servicio systemd configurado (opcional)
- [ ] Bot funcionando correctamente
- [ ] Logs verificados sin errores

---

**¡Listo!** Tu bot debería estar funcionando en Hostinger. 🎉

