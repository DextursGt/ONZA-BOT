# 🎮 Módulo Fortnite para ONZA-BOT

Este módulo extiende ONZA-BOT con funcionalidades de Fortnite usando la API oficial de Epic Games.

## 🔐 Seguridad

**IMPORTANTE**: Todos los comandos de este módulo están restringidos exclusivamente al owner del bot.

- **ID Autorizado**: `857134594028601364`
- **Verificación**: Por ID de usuario, no por roles
- **Sin excepciones**: Ni administradores ni otros roles pueden usar estos comandos

### 🛡️ Medidas Anti-Baneo Implementadas

El módulo incluye múltiples capas de seguridad para prevenir baneos:

1. **Rate Limiting Inteligente**
   - Límites por tipo de acción (ej: 3 regalos/minuto, 5 amigos/minuto)
   - Cooldown global entre acciones (mínimo 0.5s)
   - Limpieza automática de historial antiguo

2. **Delays Naturales**
   - Delays aleatorios entre acciones para simular comportamiento humano
   - Variación humana (a veces más rápido, a veces más lento)
   - Delays post-acción para evitar patrones detectables

3. **Registro de Acciones**
   - Todas las acciones se registran internamente
   - Incluye timestamp, usuario, detalles y resultado
   - Últimas 1000 acciones mantenidas para auditoría

4. **Confirmaciones Previas para Regalos**
   - Los regalos requieren confirmación explícita antes de enviarse
   - Botones interactivos para confirmar/cancelar
   - Timeout de 5 minutos para confirmaciones pendientes

5. **Validación de Tokens OAuth**
   - Verifica que todos los tokens provienen de OAuth oficial de Epic
   - Valida formato y estructura de tokens
   - Rechaza tokens no oficiales o inválidos

6. **Cifrado de Tokens**
   - Tokens almacenados cifrados con Fernet (AES-128)
   - Clave de cifrado persistente o desde variable de entorno
   - Nunca se almacenan tokens en texto plano

7. **Cumplimiento de TOS de Epic Games**
   - Valida que todas las acciones están permitidas según TOS
   - Límites diarios por cuenta (ej: 10 regalos/día, 20 amigos/día)
   - Límite de llamadas API por hora (1000/hora)
   - Rechaza acciones que violan TOS antes de ejecutarlas

## 📋 Requisitos

1. **Cuentas de Epic Games**: Hasta 5 cuentas propias
2. **OAuth de Epic Games**: Device Auth tokens para cada cuenta
3. **Dependencias**: Ver `requirements.txt` (incluye `cryptography`)

## 🚀 Configuración

### 1. Variables de Entorno (Opcional)

Para mayor seguridad, puedes establecer una clave de cifrado personalizada:

```env
FORTNITE_ENCRYPTION_KEY=tu_clave_generada_con_fernet
```

Si no se establece, se generará automáticamente y se guardará en `.fortnite_key`.

### 2. Obtener Device Auth Tokens

Para agregar cuentas, necesitas obtener Device Auth tokens de Epic Games:

**Opción A: DeviceAuthGenerator (Recomendado)**
1. Descarga DeviceAuthGenerator desde GitHub: https://github.com/xMistt/DeviceAuthGenerator
2. Ejecuta la herramienta y sigue las instrucciones
3. Obtendrás `device_code` y `user_code`
4. Usa estos códigos con `/fn_add_account`

**Opción B: Manual (Avanzado)**
1. Visita el portal de desarrolladores de Epic Games
2. Crea una aplicación OAuth
3. Usa Device Auth flow para obtener `device_code` y `user_code`
4. Autoriza el dispositivo en la web de Epic Games
5. Usa estos códigos con `/fn_add_account`

**📖 Ver guía completa**: `TOKENS_GUIDE.md`

**Nota**: Los tokens se almacenan cifrados en la base de datos del bot.

## 📚 Comandos Disponibles

### Gestión de Cuentas

- `/fn_add_account` - Agregar una nueva cuenta (máximo 5)
  - `account_number`: Número de cuenta (1-5)
  - `account_name`: Nombre descriptivo
  - `device_code`: Código de dispositivo OAuth
  - `user_code`: Código de usuario OAuth

- `/fn_switch [número]` - Cambiar cuenta activa
  - `account_number`: Número de cuenta a activar (1-5)

- `/fn_list_accounts` - Listar todas las cuentas registradas

### Gestión de Amigos

- `/fn_add_friend [username]` - Agregar un amigo
  - `username`: Nombre de usuario de Epic Games

- `/fn_list_friends` - Listar todos los amigos

### Regalos

- `/fn_gift [username] [item_id]` - **Preparar** un regalo (requiere confirmación)
  - `username`: Usuario destinatario
  - `item_id`: ID del item a regalar
  - **Nota**: Este comando solo prepara el regalo. Debes confirmarlo después.

- `/fn_gift_confirm [confirmation_id]` - Confirmar y enviar un regalo preparado
  - `confirmation_id`: ID de confirmación del regalo preparado

- `/fn_gift_cancel [confirmation_id]` - Cancelar un regalo preparado
  - `confirmation_id`: ID de confirmación del regalo a cancelar

- `/fn_gift_message [mensaje]` - Establecer mensaje personalizado para regalos

### Tienda

- `/fn_store` - Ver la tienda actual de Fortnite

- `/fn_item_info [item_id]` - Obtener información detallada de un item

## 🏗️ Estructura del Módulo

```
fortnite/
├── __init__.py          # Exportaciones del módulo
├── security.py          # Verificación de permisos por ID
├── auth.py              # Autenticación OAuth con Epic Games
├── accounts.py          # Gestión de hasta 5 cuentas
├── friends.py           # Agregar y listar amigos
├── gifting.py           # Enviar regalos
├── store.py             # Ver tienda e items
└── fortnite_cog.py      # Cog principal con todos los comandos
```

## 🔒 Almacenamiento de Datos

- **Tokens**: Cifrados con Fernet (AES-128)
- **Cuentas**: Almacenadas en `data/bot_data.json` bajo la clave `fortnite_accounts`
- **Clave de cifrado**: Guardada en `.fortnite_key` o variable de entorno

## ⚠️ Limitaciones y Consideraciones

1. **Rate Limiting**: El módulo implementa rate limiting inteligente con delays naturales. Los límites son:
   - Regalos: 3 por minuto, 10 por día por cuenta
   - Agregar amigos: 5 por minuto, 20 por día por cuenta
   - Consultas de tienda: 20 por minuto
   - Consultas de items: 30 por minuto
   - Llamadas API totales: 1000 por hora por cuenta

2. **Confirmaciones de Regalos**: Los regalos requieren confirmación explícita para prevenir envíos accidentales. Las confirmaciones expiran después de 5 minutos.

3. **Tokens Expirados**: Los tokens se refrescan automáticamente cuando es posible. Si falla el refresh, será necesario re-autenticar la cuenta.

4. **API de Epic Games**: Algunos endpoints pueden cambiar. El módulo incluye fallbacks cuando es posible.

5. **TOS de Epic Games**: Este módulo cumple estrictamente con los TOS:
   - Solo usa OAuth oficial (no maneja credenciales)
   - Valida todas las acciones antes de ejecutarlas
   - Respeta límites diarios y por hora
   - Registra todas las acciones para auditoría

6. **Delays Naturales**: El módulo incluye delays aleatorios entre acciones para simular comportamiento humano y evitar detección de bots.

## 🐛 Solución de Problemas

### Error: "No se pudo obtener token de acceso válido"
- Verifica que la cuenta esté correctamente autenticada
- Intenta refrescar la cuenta o re-agregarla

### Error: "No hay cuenta activa"
- Usa `/fn_list_accounts` para ver cuentas disponibles
- Usa `/fn_switch` para activar una cuenta

### Error: "Límite de 5 cuentas alcanzado"
- Elimina una cuenta existente antes de agregar una nueva
- (Nota: No hay comando para eliminar, se puede hacer manualmente editando `data/bot_data.json`)

## 📝 Notas de Desarrollo

- Todos los comandos son slash commands de Discord
- Los mensajes son ephemeral (solo visibles para el usuario)
- El módulo se integra automáticamente con el sistema de logging del bot
- Los errores se registran en los logs del bot

## 🔄 Actualizaciones Futuras

Posibles mejoras:
- Comando para eliminar cuentas
- Cache más robusto para la tienda
- Mejor manejo de rate limiting
- Soporte para más operaciones de la API de Epic Games

---

**Desarrollado para ONZA-BOT**  
*Solo para uso del owner autorizado (ID: 857134594028601364)*

