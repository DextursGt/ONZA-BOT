# 🔌 APIs Necesarias para el Módulo Fortnite

## 📋 Resumen de APIs

El módulo de Fortnite utiliza las APIs oficiales de Epic Games. **NO se requiere ninguna API key externa** - solo necesitas tokens OAuth de tus propias cuentas de Epic Games.

## 🔐 APIs de Epic Games Utilizadas

### 1. **OAuth / Autenticación**
- **Base URL**: `https://account-public-service-prod03.ol.epicgames.com`
- **Endpoints**:
  - `/account/api/oauth/deviceAuthorization` - Obtener códigos de dispositivo
  - `/account/api/oauth/token` - Intercambiar códigos por tokens
- **Método**: Device Auth Flow (OAuth 2.0)
- **Requisitos**: 
  - Cuenta de Epic Games
  - Device Auth Generator o acceso manual al portal de Epic

### 2. **API de Catálogo/Tienda**
- **Base URL**: `https://catalog-public-service-prod.ol.epicgames.com/catalog/api/shared`
- **Endpoint**: `/namespace/fortnite`
- **Método**: GET con token de acceso
- **Requisitos**: Token de acceso válido de OAuth

### 3. **API de Amigos**
- **Base URL**: `https://friends-public-service-prod.ol.epicgames.com`
- **Endpoints**:
  - `/friends/api/public/friends/{accountId}` - Listar amigos
  - `/friends/api/public/friends/{accountId}/{friendId}` - Agregar amigo
- **Método**: GET/POST con token de acceso
- **Requisitos**: Token de acceso válido de OAuth

### 4. **API de Regalos**
- **Base URL**: `https://gifting-public-service-prod.ol.epicgames.com`
- **Endpoints**:
  - `/gifting/api/public/gifts/{accountId}` - Enviar regalo
- **Método**: POST con token de acceso
- **Requisitos**: Token de acceso válido de OAuth

## 🎯 Lo que NO necesitas

❌ **NO necesitas**:
- API keys de terceros
- Claves de desarrollador de Epic Games
- Acceso a APIs no oficiales
- Tokens de aplicaciones externas

✅ **Solo necesitas**:
- Tokens OAuth de tus propias cuentas de Epic Games
- Device Auth codes (obtenidos con DeviceAuthGenerator)

## 📝 Cómo Obtener los Tokens

### Opción 1: DeviceAuthGenerator (Recomendado)

1. Descarga DeviceAuthGenerator:
   - GitHub: https://github.com/xMistt/DeviceAuthGenerator
   - O busca "DeviceAuthGenerator Epic Games" en GitHub

2. Ejecuta la herramienta y sigue las instrucciones:
   - Te dará un `device_code` y `user_code`
   - Visita la URL que te proporciona
   - Autoriza el dispositivo con tu cuenta de Epic Games

3. Usa los códigos con el comando:
   ```
   !fn_add_account 1 "Mi Cuenta" <device_code> <user_code>
   ```

### Opción 2: Manual (Avanzado)

1. Visita: https://www.epicgames.com/id/login
2. Inicia sesión con tu cuenta
3. Ve a: https://www.epicgames.com/id/api/oauth/authorize
4. Sigue el flujo de Device Auth
5. Obtén `device_code` y `user_code`

## 🔑 Variables de Entorno (Opcional)

Puedes configurar una clave de cifrado personalizada en `.env`:

```env
FORTNITE_ENCRYPTION_KEY=tu_clave_generada_con_fernet
```

Si no la configuras, se generará automáticamente y se guardará en `.fortnite_key`.

## 📚 Documentación Oficial

- **Epic Games OAuth**: https://dev.epicgames.com/docs/services/en-US/EpicAccountServices/DeviceAuth/index.html
- **Epic Games API**: https://dev.epicgames.com/docs/services

## ⚠️ Importante

- Todos los tokens se almacenan **cifrados** en la base de datos
- Los tokens tienen expiración y se refrescan automáticamente
- Solo puedes usar tus propias cuentas (máximo 5)
- Todas las acciones están limitadas por rate limiting y TOS de Epic

