# 🔐 Configuración de Credenciales

## ⚠️ IMPORTANTE: Seguridad

**NUNCA subas tus credenciales a GitHub.** Todas las credenciales sensibles deben estar en el archivo `.env` que está en `.gitignore`.

## 📋 Variables de Entorno Requeridas

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

### Fortnite DeviceAuth (PRIMARY_ACCOUNT)

```env
# Fortnite DeviceAuth - Credenciales sensibles
# Obtén estas credenciales usando DeviceAuthGenerator
FORTNITE_DEVICE_ID=tu_device_id_aqui
FORTNITE_ACCOUNT_ID=tu_account_id_aqui
FORTNITE_SECRET=tu_secret_aqui
FORTNITE_USER_AGENT=DeviceAuthGenerator/1.3.0 Windows/10.0.26100
```

### Ejemplo de archivo .env completo

```env
# Discord Bot Token
DISCORD_TOKEN=tu_token_de_discord

# Fortnite DeviceAuth (PRIMARY_ACCOUNT)
FORTNITE_DEVICE_ID=a2643223ecab487495422fa1aa7a9e98
FORTNITE_ACCOUNT_ID=e8c72f4edf924aab8d0701f492c0c83e
FORTNITE_SECRET=F3LI2FF5NSXYJH6WRM6P3RS7YD2GMENQ
FORTNITE_USER_AGENT=DeviceAuthGenerator/1.3.0 Windows/10.0.26100

# Fortnite API (opcional)
FORTNITE_API_KEY=tu_api_key_aqui
```

## 🚀 Configuración Rápida

1. **Copia el archivo de ejemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Edita `.env` y agrega tus credenciales reales**

3. **Verifica que `.env` esté en `.gitignore`** (ya está configurado)

4. **Reinicia el bot** para que cargue las nuevas variables

## ✅ Verificación

Para verificar que las credenciales están configuradas correctamente:

```bash
# En el servidor VPS
cd /root/ONZA-BOT
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DEVICE_ID:', 'OK' if os.getenv('FORTNITE_DEVICE_ID') else 'FALTANTE')"
```

## 🔒 Seguridad Adicional

- ✅ `.env` está en `.gitignore` - NO se subirá a GitHub
- ✅ Las credenciales se cargan desde variables de entorno
- ✅ No hay credenciales hardcodeadas en el código
- ✅ El código está limpio y listo para compartir

## 📝 Notas

- Si las variables no están configuradas, el bot mostrará un error en los logs
- El bot NO funcionará sin estas credenciales
- Asegúrate de tener permisos correctos en el archivo `.env` (chmod 600)

