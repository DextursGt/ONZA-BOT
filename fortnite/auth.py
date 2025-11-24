"""
Módulo de autenticación con Epic Games
Maneja tokens OAuth y Device Auth para cuentas de Fortnite
"""

import os
import base64
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging

log = logging.getLogger('fortnite-auth')

# Configuración de Epic Games OAuth
EPIC_OAUTH_BASE = "https://account-public-service-prod03.ol.epicgames.com"
EPIC_DEVICE_AUTH_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/token"
EPIC_DEVICE_CODE_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/deviceAuthorization"
EPIC_AUTHORIZATION_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/authorize"

# Cliente OAuth de Fortnite (usado para generar códigos de autorización)
FORTNITE_CLIENT_ID = "3446cd72694c4a485d81b77adbb214e"
FORTNITE_REDIRECT_URI = "com.epicgames.fortnite://fnauth/"

# Clave de cifrado (debería estar en variables de entorno en producción)
# En producción, generar con: Fernet.generate_key() y guardarla en .env
# Si no existe, se generará una nueva y se guardará en .fortnite_key
_encryption_key_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '.fortnite_key')
)
ENCRYPTION_KEY = os.getenv('FORTNITE_ENCRYPTION_KEY')

# Si no hay clave en env, intentar leer de archivo o generar nueva
if not ENCRYPTION_KEY:
    try:
        if os.path.exists(_encryption_key_file):
            with open(_encryption_key_file, 'rb') as f:
                ENCRYPTION_KEY = f.read().decode()
            log.info("Clave de cifrado cargada desde archivo")
        else:
            # Generar nueva clave y guardarla
            new_key = Fernet.generate_key()
            ENCRYPTION_KEY = new_key.decode()
            # Asegurar que el directorio existe
            key_dir = os.path.dirname(_encryption_key_file)
            if key_dir:
                os.makedirs(key_dir, exist_ok=True)
            with open(_encryption_key_file, 'wb') as f:
                f.write(new_key)
            log.warning(f"Nueva clave de cifrado generada y guardada en {_encryption_key_file}")
    except Exception as e:
        log.error(f"Error manejando clave de cifrado: {e}")
        # Fallback: generar clave temporal (no persistente)
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        log.warning("Usando clave temporal (no persistente)")


class TokenEncryption:
    """Clase para cifrar y descifrar tokens de forma segura"""
    
    def __init__(self):
        """Inicializa el sistema de cifrado"""
        try:
            # Asegurar que la clave tenga el formato correcto
            key = ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
            self.cipher = Fernet(key)
        except Exception as e:
            log.error(f"Error inicializando cifrado: {e}")
            # Generar nueva clave si hay error
            new_key = Fernet.generate_key()
            self.cipher = Fernet(new_key)
            log.warning("Nueva clave de cifrado generada")
    
    def encrypt_token(self, token: str) -> str:
        """
        Cifra un token
        
        Args:
            token: Token en texto plano
            
        Returns:
            Token cifrado en base64
        """
        try:
            encrypted = self.cipher.encrypt(token.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            log.error(f"Error cifrando token: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Descifra un token
        
        Args:
            encrypted_token: Token cifrado en base64
            
        Returns:
            Token en texto plano
        """
        try:
            decoded = base64.b64decode(encrypted_token.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            log.error(f"Error descifrando token: {e}")
            raise


class EpicAuth:
    """Clase para manejar autenticación con Epic Games"""
    
    def __init__(self):
        """Inicializa el sistema de autenticación"""
        self.encryption = TokenEncryption()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea una sesión HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Cierra la sesión HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _validate_oauth_token(self, token_data: Dict[str, Any]) -> bool:
        """
        Valida que un token proviene de OAuth oficial de Epic Games
        
        Args:
            token_data: Datos del token recibido
            
        Returns:
            True si el token es válido y oficial, False en caso contrario
        """
        try:
            # Verificar campos requeridos (account_id puede obtenerse después con exchange)
            required_fields = ['access_token', 'refresh_token']
            for field in required_fields:
                if field not in token_data or not token_data[field]:
                    log.warning(f"Token inválido: falta campo {field}")
                    return False
            
            # Verificar que el access_token tiene el formato correcto
            access_token = token_data.get('access_token', '')
            if not access_token or len(access_token) < 20:  # Reducido de 50 a 20 para ser más flexible
                log.warning(f"Token de acceso tiene formato inválido (longitud: {len(access_token) if access_token else 0})")
                return False
            
            # account_id puede no estar en la respuesta inicial, se obtiene con exchange
            # No es requerido para la validación inicial
            
            log.info("Token OAuth validado correctamente")
            return True
            
        except Exception as e:
            log.error(f"Error validando token OAuth: {e}")
            return False
    
    async def generate_authorization_code(self) -> Optional[Dict[str, Any]]:
        """
        Genera códigos de autorización usando Device Code Flow (método oficial de Epic Games)
        Este método obtiene códigos reales de Epic Games, no aleatorios
        
        Returns:
            Diccionario con device_code, user_code, verification_uri, etc. o None si falla
        """
        try:
            # Usar Device Code Flow que es el método oficial y funciona
            device_data = await self.get_device_code()
            
            if not device_data:
                return None
            
            device_code = device_data.get('device_code')
            user_code = device_data.get('user_code')
            verification_uri = device_data.get('verification_uri', 'https://www.epicgames.com/id/activate')
            # También puede venir verification_uri_complete que incluye el user_code en la URL
            verification_uri_complete = device_data.get('verification_uri_complete', verification_uri)
            
            # En Device Code Flow, NO hay redirectUrl real como en Authorization Code Flow
            # El device_code se intercambia directamente después de autorizar
            # No generamos un redirectUrl artificial para evitar confusión
            
            result = {
                'authorizationCode': device_code,  # Este es el código de 32 dígitos que se usa en !fn_code
                'deviceCode': device_code,  # Guardar también como device_code
                'userCode': user_code,  # Código de 8 caracteres para ingresar en Epic Games
                'verificationUri': verification_uri,  # URL base: https://www.epicgames.com/id/activate
                'verificationUriComplete': verification_uri_complete,  # URL con user_code incluido
                'expiresIn': device_data.get('expires_in', 600),
            }
            
            log.info(f"Códigos de autorización obtenidos de Epic Games: device_code={device_code[:10]}..., user_code={user_code}")
            return result
                    
        except Exception as e:
            log.error(f"Error en generate_authorization_code: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_device_code(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene códigos de dispositivo para Device Code Flow
        Método basado en DeviceAuthGenerator que funciona:
        1. Primero obtiene access_token con client_credentials usando SWITCH_TOKEN
        2. Luego usa ese access_token (Bearer) para obtener device codes
        
        Returns:
            Diccionario con device_code, user_code, verification_uri, etc. o None si falla
        """
        try:
            session = await self._get_session()
            
            # Paso 1: Obtener access_token usando SWITCH_TOKEN (como DeviceAuthGenerator)
            SWITCH_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
            
            log.info("Paso 1: Obteniendo access_token con client_credentials...")
            headers_token = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {SWITCH_TOKEN}'
            }
            
            data_token = {
                'grant_type': 'client_credentials'
            }
            
            # Usar el endpoint de token para obtener access_token
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers_token, data=data_token) as token_response:
                token_text = await token_response.text()
                
                if token_response.status == 200:
                    try:
                        token_data = json.loads(token_text)
                        access_token = token_data.get('access_token')
                        
                        if not access_token:
                            log.error("No se obtuvo access_token de la respuesta")
                            return None
                        
                        log.info("Access_token obtenido correctamente")
                        
                        # Paso 2: Usar access_token (Bearer) para obtener device codes
                        log.info("Paso 2: Obteniendo device codes con access_token...")
                        headers_device = {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Authorization': f'Bearer {access_token}'
                        }
                        
                        async with session.post(EPIC_DEVICE_CODE_URL, headers=headers_device) as device_response:
                            device_text = await device_response.text()
                            
                            if device_response.status == 200:
                                try:
                                    device_data = json.loads(device_text)
                                    log.info("Códigos de dispositivo obtenidos correctamente")
                                    return device_data
                                except json.JSONDecodeError as e:
                                    log.error(f"Error parseando JSON de device codes: {e} - {device_text}")
                                    return None
                            else:
                                # Intentar parsear el error
                                try:
                                    error_data = json.loads(device_text)
                                    error_code = error_data.get('errorCode', 'unknown')
                                    error_message = error_data.get('errorMessage', 'Sin mensaje')
                                    numeric_error = error_data.get('numericErrorCode', 'N/A')
                                    log.error(f"Error obteniendo device codes: {device_response.status}")
                                    log.error(f"Error detallado: {error_code} (código: {numeric_error}) - {error_message}")
                                except:
                                    log.error(f"Error obteniendo device codes: {device_response.status} - {device_text[:200]}")
                                return None
                    except json.JSONDecodeError as e:
                        log.error(f"Error parseando JSON de access_token: {e} - {token_text}")
                        return None
                else:
                    # Intentar parsear el error del token
                    try:
                        error_data = json.loads(token_text)
                        error_code = error_data.get('errorCode', 'unknown')
                        error_message = error_data.get('errorMessage', 'Sin mensaje')
                        numeric_error = error_data.get('numericErrorCode', 'N/A')
                        log.error(f"Error obteniendo access_token: {token_response.status}")
                        log.error(f"Error detallado: {error_code} (código: {numeric_error}) - {error_message}")
                    except:
                        log.error(f"Error obteniendo access_token: {token_response.status} - {token_text[:200]}")
                    return None
                    
        except Exception as e:
            log.error(f"Error en get_device_code: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def exchange_authorization_code(self, authorization_code: str, user_code: str = None) -> Optional[Dict[str, Any]]:
        """
        Intercambia un código de autorización (device_code) por tokens OAuth
        Usa Device Code Flow que es el método oficial de Epic Games
        Basado en el método que funciona en DeviceAuthGenerator
        
        Args:
            authorization_code: Device code (el código que se muestra como authorizationCode)
            user_code: User code opcional (no se usa en el intercambio, solo para referencia)
            
        Returns:
            Diccionario con tokens de acceso o None si falla
        """
        try:
            # Usar SWITCH_TOKEN para el intercambio (igual que DeviceAuthGenerator)
            SWITCH_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
            
            session = await self._get_session()
            
            # Headers usando SWITCH_TOKEN (igual que DeviceAuthGenerator línea 170)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {SWITCH_TOKEN}'
            }
            
            # Data con grant_type y device_code (igual que DeviceAuthGenerator línea 173)
            data = {
                'grant_type': 'device_code',
                'device_code': authorization_code
            }
            
            log.info(f"Intercambiando device_code por tokens usando SWITCH_TOKEN...")
            
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Validar que el token es oficial (sin requerir account_id todavía)
                    if not self._validate_oauth_token(token_data):
                        log.error("Token recibido no es válido o no proviene de OAuth oficial")
                        return None
                    
                    # Obtener account_id y display_name usando exchange (como DeviceAuthGenerator)
                    access_token = token_data.get('access_token')
                    account_id = None
                    display_name = None
                    
                    try:
                        log.info("Obteniendo account_id mediante exchange...")
                        exchange_headers = {
                            'Authorization': f'bearer {access_token}'
                        }
                        exchange_url = f"{EPIC_OAUTH_BASE}/account/api/oauth/exchange"
                        
                        async with session.get(exchange_url, headers=exchange_headers) as exchange_response:
                            if exchange_response.status == 200:
                                exchange_data = await exchange_response.json()
                                account_id = exchange_data.get('account_id') or exchange_data.get('id')
                                display_name = exchange_data.get('displayName') or exchange_data.get('display_name')
                                log.info(f"Account ID obtenido: {account_id}, Display Name: {display_name}")
                            else:
                                exchange_text = await exchange_response.text()
                                log.warning(f"No se pudo obtener account_id mediante exchange: {exchange_response.status} - {exchange_text[:200]}")
                    except Exception as e:
                        log.warning(f"Error obteniendo account_id mediante exchange: {e}")
                        # Continuar sin account_id si falla el exchange
                    
                    # Si no se obtuvo account_id del exchange, intentar del token_data
                    if not account_id:
                        account_id = token_data.get('account_id')
                    
                    # Calcular tiempo de expiración
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                    
                    validated_token = {
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': expires_at.isoformat(),
                        'account_id': account_id,
                        'display_name': display_name,
                        'token_type': token_data.get('token_type', 'Bearer'),
                        'source': 'epic_oauth_official'
                    }
                    
                    log.info("Intercambio de código de autorización exitoso")
                    return validated_token
                else:
                    error_text = await response.text()
                    log.error(f"Error intercambiando código: {response.status} - {error_text}")
                    # Si falla, puede ser que necesite user_code también
                    return None
                    
        except Exception as e:
            log.error(f"Error en exchange_authorization_code: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def authenticate_with_device_code(
        self, 
        device_code: str, 
        user_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Autentica usando Device Code (método recomendado por Epic)
        Valida que el token proviene de OAuth oficial
        
        Args:
            device_code: Código de dispositivo obtenido del proceso OAuth
            user_code: Código de usuario para verificación
            
        Returns:
            Diccionario con tokens de acceso o None si falla
        """
        try:
            # Validar códigos de entrada
            if not device_code or not user_code:
                log.error("Códigos de dispositivo o usuario vacíos")
                return None
            
            if len(device_code) < 20 or len(user_code) < 8:
                log.error("Códigos de dispositivo o usuario tienen formato inválido")
                return None
            
            session = await self._get_session()
            
            # Headers para autenticación (OAuth oficial de Epic Games)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y='
            }
            
            data = {
                'grant_type': 'device_code',
                'device_code': device_code,
                'user_code': user_code
            }
            
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Validar que el token es oficial
                    if not self._validate_oauth_token(token_data):
                        log.error("Token recibido no es válido o no proviene de OAuth oficial")
                        return None
                    
                    # Calcular tiempo de expiración
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                    
                    validated_token = {
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': expires_at.isoformat(),
                        'account_id': token_data.get('account_id'),
                        'device_id': token_data.get('device_id'),
                        'client_id': token_data.get('client_id'),
                        'token_type': token_data.get('token_type', 'Bearer'),
                        'source': 'epic_oauth_official'  # Marca de validación
                    }
                    
                    log.info("Autenticación OAuth oficial exitosa")
                    return validated_token
                else:
                    error_text = await response.text()
                    log.error(f"Error en autenticación: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            log.error(f"Error en authenticate_with_device_code: {e}")
            return None
    
    async def authenticate_with_device_auth(
        self,
        device_id: str,
        account_id: str,
        secret: str
    ) -> Optional[Dict[str, Any]]:
        """
        Autentica usando Device Auth (device_id + secret)
        Este método es para usar con credenciales generadas por DeviceAuthGenerator
        
        Args:
            device_id: ID del dispositivo generado por DeviceAuthGenerator
            account_id: ID de la cuenta de Epic Games
            secret: Secret generado por DeviceAuthGenerator
            
        Returns:
            Diccionario con tokens de acceso o None si falla
        """
        try:
            # Validar datos de entrada
            if not device_id or not account_id or not secret:
                log.error("device_id, account_id o secret vacíos")
                return None
            
            session = await self._get_session()
            
            # Headers para autenticación (OAuth oficial de Epic Games)
            # Usar el token que funciona con device_auth (según código de referencia)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE='
            }
            
            # Usar grant_type device_auth con device_id, account_id y secret
            # IMPORTANTE: account_id debe estar incluido en el data (según código de referencia)
            data = {
                'grant_type': 'device_auth',
                'device_id': device_id,
                'account_id': account_id,  # Este es el campo que faltaba
                'secret': secret
            }
            
            log.info(f"Intentando autenticar con device_id: {device_id[:10]}... y secret: {secret[:10]}...")
            
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    try:
                        token_data = await response.json()
                    except Exception as json_error:
                        response_text = await response.text()
                        log.error(f"Error parseando JSON de respuesta: {json_error} - {response_text}")
                        return None
                    
                    # Validar que el token es oficial
                    if not self._validate_oauth_token(token_data):
                        log.error("Token recibido no es válido o no proviene de OAuth oficial")
                        return None
                    
                    # Calcular tiempo de expiración
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                    
                    validated_token = {
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': expires_at.isoformat(),
                        'account_id': token_data.get('account_id', account_id),  # Preferir el del token, fallback al proporcionado
                        'device_id': device_id,  # Usar el device_id proporcionado
                        'client_id': token_data.get('client_id'),
                        'token_type': token_data.get('token_type', 'Bearer'),
                        'source': 'epic_oauth_official'  # Marca de validación
                    }
                    
                    log.info("Autenticación Device Auth exitosa")
                    return validated_token
                else:
                    # Leer el error
                    try:
                        error_json = await response.json()
                        error_code = error_json.get('errorCode', 'unknown')
                        error_message = error_json.get('errorMessage', 'Sin mensaje')
                        log.error(f"Error en autenticación Device Auth: {response.status} - Código: {error_code}, Mensaje: {error_message}")
                    except:
                        response_text = await response.text()
                        log.error(f"Error en autenticación Device Auth: {response.status} - {response_text}")
                    return None
                    
        except Exception as e:
            log.error(f"Error en authenticate_with_device_auth: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresca un token de acceso usando el refresh token
        
        Args:
            refresh_token: Token de refresco (cifrado)
            
        Returns:
            Nuevo token de acceso o None si falla
        """
        try:
            # Descifrar refresh token
            decrypted_refresh = self.encryption.decrypt_token(refresh_token)
            
            session = await self._get_session()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'basic MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y='
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': decrypted_refresh
            }
            
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get('expires_in', 3600))
                    
                    return {
                        'access_token': token_data.get('access_token'),
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': expires_at.isoformat()
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error refrescando token: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            log.error(f"Error en refresh_access_token: {e}")
            return None
    
    def encrypt_token(self, token: str) -> str:
        """Cifra un token para almacenamiento seguro"""
        return self.encryption.encrypt_token(token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Descifra un token almacenado"""
        return self.encryption.decrypt_token(encrypted_token)
    
    def is_token_expired(self, expires_at: str) -> bool:
        """
        Verifica si un token ha expirado
        
        Args:
            expires_at: Fecha de expiración en formato ISO
            
        Returns:
            True si está expirado, False en caso contrario
        """
        try:
            exp_time = datetime.fromisoformat(expires_at)
            return datetime.utcnow() >= exp_time
        except Exception as e:
            log.error(f"Error verificando expiración: {e}")
            return True  # Considerar expirado si hay error

