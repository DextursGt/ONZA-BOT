# 🎫 Guía de Tokens para Fortnite API

Esta guía explica qué tokens necesitas y cómo obtenerlos para usar el módulo de Fortnite.

## 📋 Tokens Necesarios

Para que el bot pueda acceder a tu cuenta de Fortnite y realizar acciones, necesitas **2 tokens principales**:

### 1. **Access Token** (Token de Acceso)
- **Qué es**: Token que permite hacer peticiones a la API de Epic Games
- **Duración**: Generalmente expira en 1-8 horas
- **Uso**: Se usa en cada petición a la API (ver tienda, agregar amigos, enviar regalos)
- **Renovación**: Se renueva automáticamente usando el refresh token

### 2. **Refresh Token** (Token de Renovación)
- **Qué es**: Token que permite obtener nuevos access tokens sin volver a autenticarte
- **Duración**: Generalmente válido por semanas o meses
- **Uso**: Se usa automáticamente cuando el access token expira
- **Importante**: Guarda este token de forma segura, es tu "llave maestra"

## 🔐 Cómo Obtener los Tokens

Epic Games usa **OAuth 2.0 Device Code Flow**, que es seguro y no requiere que compartas tu contraseña.

### Opción 1: Usar Device Auth Generator (Recomendado)

La forma más fácil es usar una herramienta como **DeviceAuthGenerator**:

1. **Descargar DeviceAuthGenerator**:
   - Repositorio: https://github.com/xMistt/DeviceAuthGenerator
   - O busca "Epic Games Device Auth Generator" en GitHub

2. **Ejecutar la herramienta**:
   ```bash
   # Ejemplo (depende de la herramienta específica)
   python device_auth_generator.py
   ```

3. **Seguir las instrucciones**:
   - Te dará un `device_code` y un `user_code`
   - Visita la URL que te indique
   - Ingresa el `user_code` en la página de Epic Games
   - Autoriza el dispositivo

4. **Obtener los tokens**:
   - La herramienta te dará los tokens o los códigos necesarios
   - Usa estos códigos con `/fn_add_account` en Discord

### Opción 2: OAuth Manual (Avanzado)

Si prefieres hacerlo manualmente:

#### Paso 1: Obtener Device Code

```bash
curl -X POST "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/deviceAuthorization" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y=" \
  -d "grant_type=client_credentials"
```

Esto te dará:
- `device_code`: Código del dispositivo
- `user_code`: Código para ingresar en la web
- `verification_uri`: URL donde ingresar el código
- `expires_in`: Tiempo de expiración

#### Paso 2: Autorizar el Dispositivo

1. Visita la `verification_uri` (generalmente: https://www.epicgames.com/id/activate)
2. Ingresa el `user_code`
3. Inicia sesión con tu cuenta de Epic Games
4. Autoriza el dispositivo

#### Paso 3: Intercambiar por Tokens

```bash
curl -X POST "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y=" \
  -d "grant_type=device_code" \
  -d "device_code=TU_DEVICE_CODE" \
  -d "user_code=TU_USER_CODE"
```

Esto te dará:
- `access_token`: Token de acceso
- `refresh_token`: Token de renovación
- `expires_in`: Tiempo hasta expiración
- `account_id`: ID de tu cuenta

## 🚀 Usar los Tokens en el Bot

Una vez que tengas los códigos o tokens, úsalos así:

### Método 1: Con Device Code y User Code (Recomendado)

Si tienes `device_code` y `user_code`:

```
/fn_add_account account_number:1 account_name:Mi Cuenta Principal device_code:TU_DEVICE_CODE user_code:TU_USER_CODE
```

El bot automáticamente:
1. Intercambiará los códigos por tokens
2. Validará que los tokens son oficiales
3. Cifrará y guardará los tokens de forma segura

### Método 2: Con Tokens Directos (Si ya los tienes)

Si ya tienes `access_token` y `refresh_token`, necesitarías modificar el código para aceptarlos directamente (no está implementado por defecto por seguridad).

## 🔍 Verificar que los Tokens Funcionan

Una vez agregada la cuenta, puedes verificar que funciona:

1. **Listar cuentas**: `/fn_list_accounts`
   - Debería mostrar tu cuenta agregada

2. **Ver tienda**: `/fn_store`
   - Si funciona, verás los items de la tienda

3. **Listar amigos**: `/fn_list_friends`
   - Si funciona, verás tu lista de amigos

## 🔄 Renovación Automática de Tokens

El bot renueva automáticamente los tokens cuando expiran:

- **Access Token expirado**: Se renueva usando el refresh token
- **Refresh Token expirado**: Necesitarás agregar la cuenta nuevamente
- **Renovación silenciosa**: Ocurre automáticamente, no necesitas hacer nada

## 🛡️ Seguridad de los Tokens

### Lo que hace el bot automáticamente:

✅ **Cifrado**: Todos los tokens se cifran antes de guardarse
✅ **Validación**: Verifica que los tokens provienen de OAuth oficial
✅ **Almacenamiento seguro**: Los tokens nunca se muestran en logs
✅ **Renovación automática**: Los tokens se renuevan cuando es necesario

### Lo que debes hacer tú:

✅ **No compartir tokens**: Nunca compartas tus tokens con nadie
✅ **2FA activado**: Activa autenticación de dos factores en tu cuenta Epic
✅ **Backup de clave**: Guarda la clave de cifrado (`FORTNITE_ENCRYPTION_KEY`)
✅ **Revisar actividad**: Revisa periódicamente la actividad de tu cuenta

## 📝 Estructura de los Tokens

Cuando obtienes los tokens, recibes algo como esto:

```json
{
  "access_token": "eg1~eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eg1~refresh~eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 28800,
  "expires_at": "2024-01-15T12:00:00Z",
  "token_type": "Bearer",
  "account_id": "abc123def456...",
  "device_id": "device123...",
  "client_id": "client123..."
}
```

### Campos Importantes:

- **access_token**: Token JWT que se usa en peticiones
- **refresh_token**: Token para renovar el access token
- **expires_in**: Segundos hasta expiración (generalmente 28800 = 8 horas)
- **account_id**: ID único de tu cuenta Epic Games

## ⚠️ Problemas Comunes

### "Error al autenticar con Epic Games"

**Causas posibles**:
- Los códigos expiraron (tienen tiempo limitado)
- Los códigos ya fueron usados
- No autorizaste el dispositivo en la web

**Solución**:
- Obtén nuevos códigos
- Asegúrate de autorizar el dispositivo en la web de Epic Games

### "Token expirado"

**Causa**: El refresh token expiró o fue revocado

**Solución**:
- Agrega la cuenta nuevamente con `/fn_add_account`
- Obtén nuevos tokens

### "No se pudo obtener token de acceso válido"

**Causas posibles**:
- El access token expiró y el refresh falló
- El refresh token expiró
- Problemas de conexión con Epic Games

**Solución**:
- El bot intentará renovar automáticamente
- Si falla, agrega la cuenta nuevamente

## 🔗 Recursos Útiles

- **Epic Games Developer Portal**: https://dev.epicgames.com/
- **OAuth Documentation**: https://dev.epicgames.com/docs/services
- **DeviceAuthGenerator**: https://github.com/xMistt/DeviceAuthGenerator
- **Fortnite API Docs**: https://dev.epicgames.com/docs/services

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs del bot (`onza_bot.log`)
2. Verifica que los códigos no hayan expirado
3. Asegúrate de haber autorizado el dispositivo
4. Intenta obtener nuevos códigos

---

**Nota**: Los tokens son sensibles. Nunca los compartas públicamente ni los subas a repositorios públicos.

