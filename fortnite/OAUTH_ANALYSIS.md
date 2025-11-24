# Análisis del Flujo OAuth de Fortnite

## Estado Actual del Código

### Cliente OAuth Usado
- **Client ID**: `34a02cf8f4414e29b15921876da368da` (Epic Games Launcher PC - Oficial)
- **Client Secret**: `daafbcc7373745039dffe53d94fc75cf` (Epic Games Launcher PC - Oficial)
- **Basic Token**: `MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y=`

### Flujo Actual: Device Code Flow
El bot usa **Device Code Flow**, que es el método oficial de Epic Games para aplicaciones sin navegador (bots, CLI).

**Pasos del flujo:**
1. Obtener `access_token` con `client_credentials` usando cliente oficial Launcher
2. Usar ese `access_token` (Bearer) para solicitar `device_code` y `user_code`
3. Usuario ingresa `user_code` en `https://www.epicgames.com/id/activate`
4. Bot intercambia `device_code` por `access_token` y `refresh_token`

### Endpoints Usados
- **Token Endpoint**: `https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token`
- **Device Code Endpoint**: `https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/deviceAuthorization`
- **Verification URI**: `https://www.epicgames.com/id/activate`

### Redirect URI
- **Actual**: `com.epicgames.fortnite://fnauth/` (para Device Code Flow, no se usa realmente)
- **Nota**: Device Code Flow no requiere redirect_uri en el intercambio

### Scopes
- `basic_profile`
- `friends_list`
- `presence`
- `openid`
- `offline_access`

## Logs de Debugging Agregados

Los logs ahora muestran:
- `[DEBUG] CLIENT_ID usado`
- `[DEBUG] CLIENT_SECRET usado` (mascarado)
- `[DEBUG] BASIC_TOKEN usado` (mascarado)
- `[DEBUG] REDIRECT_URI`
- `[DEBUG] REQUEST URL`
- `[DEBUG] REQUEST HEADERS`
- `[DEBUG] REQUEST DATA`
- `[DEBUG] RESPONSE STATUS`
- `[DEBUG] RESPONSE BODY`
- `[DEBUG] ERROR_CODE` (si hay error)
- `[DEBUG] ERROR_MESSAGE` (si hay error)

## Posibles Problemas

1. **Cliente Launcher puede no tener permisos para Device Code Flow**
   - Algunos clientes oficiales solo funcionan para Authorization Code Flow
   - Device Code Flow puede requerir un cliente específico

2. **Redirect URI no coincide**
   - Device Code Flow no requiere redirect_uri en la solicitud de device_code
   - Pero puede requerirlo en el intercambio final

3. **Scopes inválidos**
   - Algunos scopes pueden estar deprecated
   - Epic puede requerir scopes específicos para Device Code Flow

4. **Falta PKCE**
   - Authorization Code Flow moderno requiere PKCE
   - Device Code Flow no requiere PKCE

## Próximos Pasos para Diagnosticar

1. Ejecutar `!fn_login` y revisar los logs `[DEBUG]`
2. Verificar qué error específico devuelve Epic Games
3. Si el cliente Launcher no funciona, considerar usar Authorization Code Flow con PKCE
4. Implementar captura manual del authorization_code si es necesario

