# 🛡️ Documentación de Seguridad Anti-Baneo

Este documento detalla todas las medidas de seguridad implementadas para prevenir baneos de Epic Games.

## 📊 Rate Limiting

### Límites por Tipo de Acción

| Acción | Por Minuto | Por Día | Por Hora |
|--------|------------|---------|----------|
| Agregar Amigos | 5 | 20 | - |
| Listar Amigos | 10 | - | - |
| Enviar Regalos | 3 | 10 | - |
| Consultar Tienda | 20 | - | - |
| Info de Items | 30 | - | - |
| Refrescar Tokens | 10 | - | - |
| Cambiar Cuenta | 5 | - | - |
| **Total API Calls** | - | - | 1000 |

### Cooldown Global

- **Mínimo**: 0.5 segundos entre cualquier acción
- **Objetivo**: Prevenir acciones demasiado rápidas que puedan ser detectadas

## ⏱️ Delays Naturales

### Delays Pre-Acción

Antes de ejecutar una acción, el sistema espera un tiempo aleatorio:

- **Agregar Amigos**: 2-5 segundos
- **Listar Amigos**: 1-3 segundos
- **Enviar Regalos**: 5-10 segundos (muy conservador)
- **Consultar Tienda**: 1-2 segundos
- **Info de Items**: 0.5-1.5 segundos
- **Refrescar Tokens**: 2-4 segundos
- **Cambiar Cuenta**: 1-2 segundos

### Delays Post-Acción

Después de ejecutar una acción, se aplica un delay adicional con variación humana:

- **Variación**: 80%, 100%, 120%, 150% del delay base
- **Objetivo**: Simular comportamiento humano impredecible

## 📝 Registro de Acciones

### Información Registrada

Cada acción registra:

- **Timestamp**: Fecha y hora exacta (ISO format)
- **Tipo de Acción**: friend_add, gift_send, etc.
- **Usuario**: ID de Discord del usuario
- **Detalles**: Parámetros específicos de la acción
- **Resultado**: Éxito o fallo
- **Error**: Mensaje de error si falló

### Retención

- **Últimas 1000 acciones**: Mantenidas en memoria
- **Limpieza automática**: Acciones antiguas se eliminan automáticamente

## ✅ Confirmaciones de Regalos

### Flujo de Confirmación

1. **Preparación**: `/fn_gift` prepara el regalo (no lo envía)
2. **Revisión**: Usuario ve detalles del regalo
3. **Confirmación**: Usuario confirma explícitamente con `/fn_gift_confirm` o botón
4. **Envío**: Solo entonces se envía el regalo

### Características

- **Timeout**: 5 minutos para confirmar
- **Botones Interactivos**: Confirmar/Cancelar en Discord
- **Validación TOS**: Se valida antes de enviar, no antes de preparar
- **Prevención de Errores**: Evita envíos accidentales

## 🔐 Validación de Tokens OAuth

### Verificaciones Realizadas

1. **Formato del Token**:
   - Longitud mínima: 50 caracteres
   - Estructura válida

2. **Campos Requeridos**:
   - `access_token`: Presente y válido
   - `refresh_token`: Presente y válido
   - `account_id`: Presente y válido (mínimo 10 caracteres)

3. **Origen OAuth**:
   - Token debe venir de endpoint oficial de Epic Games
   - Client ID válido
   - Marca `source: 'epic_oauth_official'` en tokens validados

4. **Rechazo Automático**:
   - Tokens con formato inválido
   - Tokens sin campos requeridos
   - Tokens que no pasan validación de origen

## 🔒 Cifrado de Tokens

### Algoritmo

- **Método**: Fernet (AES-128 en modo CBC)
- **Codificación**: Base64 para almacenamiento
- **Clave**: 32 bytes, generada automáticamente o desde variable de entorno

### Almacenamiento

- **Archivo**: `.fortnite_key` (en .gitignore)
- **Variable de Entorno**: `FORTNITE_ENCRYPTION_KEY` (recomendado en producción)
- **Nunca en texto plano**: Todos los tokens siempre cifrados

### Rotación de Claves

- Si se cambia la clave, los tokens antiguos no se podrán descifrar
- Se recomienda hacer backup antes de cambiar la clave

## 📋 Cumplimiento de TOS

### Validaciones TOS

1. **Acciones Permitidas**:
   - Solo acciones explícitamente permitidas por TOS
   - Lista blanca de acciones válidas

2. **Límites Diarios**:
   - Regalos: 10 por día por cuenta
   - Agregar amigos: 20 por día por cuenta
   - Se rechaza automáticamente si se excede

3. **Límites por Hora**:
   - Llamadas API: 1000 por hora por cuenta
   - Se rechaza automáticamente si se excede

4. **Validación de Parámetros**:
   - Usernames válidos (mínimo 3 caracteres)
   - Item IDs válidos
   - Destinatarios válidos

### Rechazo Preventivo

- Las acciones se validan **antes** de ejecutarse
- Si violan TOS, se rechazan inmediatamente
- Se registra el rechazo en los logs

## 🔄 Flujo de Seguridad Completo

### Ejemplo: Enviar un Regalo

1. **Usuario ejecuta** `/fn_gift username item_id`
2. **Rate Limiter**: Verifica límites y aplica delay si es necesario
3. **Preparación**: Se prepara el regalo (no se envía)
4. **Confirmación**: Usuario ve detalles y confirma
5. **Validación TOS**: Se valida que la acción está permitida
6. **Rate Limiter**: Verifica límites nuevamente
7. **Delay Natural**: Espera tiempo aleatorio
8. **Validación Token**: Verifica token válido y oficial
9. **Ejecución**: Envía el regalo
10. **Registro**: Registra la acción exitosa
11. **Delay Post-Acción**: Espera tiempo aleatorio adicional

## 📊 Monitoreo

### Estadísticas Disponibles

El rate limiter proporciona estadísticas:

```python
from fortnite.rate_limiter import get_rate_limiter

stats = get_rate_limiter().get_stats()
# Retorna: acciones en último minuto, límite, porcentaje usado
```

### Logs de Acciones

Todas las acciones se registran en los logs del bot con nivel INFO o WARNING según resultado.

## ⚠️ Recomendaciones

1. **No exceder límites**: Aunque el sistema los previene, evita llegar al límite
2. **Espaciar acciones**: No ejecutar muchas acciones seguidas
3. **Revisar confirmaciones**: Siempre revisa los detalles antes de confirmar regalos
4. **Monitorear logs**: Revisa los logs periódicamente para detectar problemas
5. **Backup de tokens**: Mantén backup de la clave de cifrado

## 🚨 Qué Hacer si Recibes un Baneo

1. **Detener inmediatamente**: No ejecutar más acciones
2. **Revisar logs**: Identificar qué acción pudo causar el baneo
3. **Esperar**: Respetar el tiempo de baneo
4. **Reducir frecuencia**: Al volver, usar límites más conservadores
5. **Contactar soporte**: Si es necesario, contactar soporte de Epic Games

---

**Última actualización**: Todas las medidas están activas y funcionando.

