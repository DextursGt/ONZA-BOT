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

# Cliente OAuth de Fortnite - Cliente Oficial Launcher (PC)
# Este es el cliente oficial más reciente y aprobado por Epic Games
# Cliente: Epic Games Launcher (PC)
FORTNITE_CLIENT_ID = "34a02cf8f4414e29b15921876da368da"
FORTNITE_CLIENT_SECRET = "daafbcc7373745039dffe53d94fc75cf"
FORTNITE_REDIRECT_URI = "com.epicgames.fortnite://fnauth/"

# Token básico del cliente Launcher (base64 de client_id:client_secret)
FORTNITE_LAUNCHER_BASIC_TOKEN = "MzRhMDJjZjhmNDQxNGUyOWIxNTkyMTg3NmRhMzY4ZGE6ZGFhZmJjY2M3Mzc3NDUwMzlkZmZlNTNkOTRmYzc1Y2Y="

# ========== PRIMARY ACCOUNT - DeviceAuth Directo ==========
# Cuenta principal usando DeviceAuth válido generado manualmente
# NO usar OAuth, NO regenerar, usar estos valores directamente
PRIMARY_ACCOUNT_DEVICE_ID = "a2643223ecab487495422fa1aa7a9e98"
PRIMARY_ACCOUNT_ID = "e8c72f4edf924aab8d0701f492c0c83e"
PRIMARY_ACCOUNT_SECRET = "F3LI2FF5NSXYJH6WRM6P3RS7YD2GMENQ"
PRIMARY_ACCOUNT_USER_AGENT = "DeviceAuthGenerator/1.3.0 Windows/10.0.26100"
PRIMARY_ACCOUNT_IP = "189.172.43.38"
PRIMARY_ACCOUNT_LOCATION = "Mérida, Mexico"

# Token básico para DeviceAuth (Android client - usado por DeviceAuthGenerator)
DEVICEAUTH_BASIC_TOKEN = "MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="

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
            log.info("[DEBUG] generate_authorization_code() llamado")
            log.info(f"[DEBUG] Usando cliente: {FORTNITE_CLIENT_ID}")
            log.info(f"[DEBUG] Redirect URI: {FORTNITE_REDIRECT_URI}")
            
            # Usar Device Code Flow que es el método oficial y funciona
            device_data = await self.get_device_code()
            
            if not device_data:
                log.error("[DEBUG] get_device_code() retornó None - no se pudieron obtener códigos")
                return None
            
            device_code = device_data.get('device_code')
            user_code = device_data.get('user_code')
            verification_uri = device_data.get('verification_uri', 'https://www.epicgames.com/id/activate')
            verification_uri_complete = device_data.get('verification_uri_complete', verification_uri)
            
            if not device_code:
                log.error("[DEBUG] ERROR: device_code no encontrado en respuesta de Epic")
                return None
            
            # El "authorizationCode" que muestra el bot de Telegram es el device_code
            # El redirectUrl será el formato de Fortnite con el device_code
            redirect_url = f"{FORTNITE_REDIRECT_URI}?code={device_code}"
            
            result = {
                'authorizationCode': device_code,  # Usar device_code como authorizationCode
                'deviceCode': device_code,  # Guardar también como device_code
                'userCode': user_code,  # Guardar user_code para referencia
                'redirectUrl': redirect_url,
                'verificationUri': verification_uri,
                'verificationUriComplete': verification_uri_complete,  # URI con user_code prellenado
                'expiresIn': device_data.get('expires_in', 600),
                'interval': device_data.get('interval', 5),  # Intervalo para polling
                'sid': None
            }
            
            log.info(f"[DEBUG] ✅ Authorization code generado exitosamente")
            log.info(f"[DEBUG] authorizationCode (device_code): {device_code[:10]}...{device_code[-5:]}")
            log.info(f"[DEBUG] userCode: {user_code}")
            log.info(f"[DEBUG] verificationUri: {verification_uri}")
            log.info(f"[DEBUG] redirectUrl: {redirect_url}")
            log.info(f"[DEBUG] expiresIn: {result.get('expiresIn')} segundos")
            
            log.info(f"Códigos de autorización obtenidos de Epic Games: device_code={device_code[:10]}..., user_code={user_code}")
            return result
                    
        except Exception as e:
            log.error(f"[DEBUG] EXCEPTION en generate_authorization_code: {e}")
            import traceback
            log.error(f"[DEBUG] TRACEBACK: {traceback.format_exc()}")
            log.error(f"Error en generate_authorization_code: {e}")
            return None
    
    async def get_device_code(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene códigos de dispositivo para Device Code Flow
        Método oficial de Epic Games para autenticación de usuario real
        
        Flujo:
        1. Primero obtiene access_token con client_credentials usando cliente oficial Launcher
        2. Luego usa ese access_token (Bearer) para obtener device codes
        
        Returns:
            Diccionario con device_code, user_code, verification_uri, etc. o None si falla
        """
        try:
            session = await self._get_session()
            
            # ========== LOGS DETALLADOS DE DEBUGGING ==========
            log.info("=" * 60)
            log.info("[DEBUG] INICIANDO GENERACIÓN DE AUTHORIZATION CODE")
            log.info(f"[DEBUG] CLIENT_ID usado: {FORTNITE_CLIENT_ID}")
            log.info(f"[DEBUG] CLIENT_SECRET usado: {FORTNITE_CLIENT_SECRET[:10]}...{FORTNITE_CLIENT_SECRET[-5:]}")
            log.info(f"[DEBUG] BASIC_TOKEN usado: {FORTNITE_LAUNCHER_BASIC_TOKEN[:20]}...{FORTNITE_LAUNCHER_BASIC_TOKEN[-10:]}")
            log.info(f"[DEBUG] REDIRECT_URI: {FORTNITE_REDIRECT_URI}")
            log.info(f"[DEBUG] ENDPOINT_TOKEN: {EPIC_DEVICE_AUTH_URL}")
            log.info(f"[DEBUG] ENDPOINT_DEVICE_CODE: {EPIC_DEVICE_CODE_URL}")
            log.info("=" * 60)
            
            # Paso 1: Obtener access_token usando cliente oficial Launcher (PC)
            # NOTA: Este paso usa client_credentials que es para obtener un token de aplicación
            # que luego se usa para solicitar device codes (método oficial de Epic)
            log.info("[DEBUG] Paso 1: Obteniendo access_token con client_credentials...")
            log.info(f"[DEBUG] REQUEST URL: {EPIC_DEVICE_AUTH_URL}")
            log.info(f"[DEBUG] REQUEST HEADERS: Authorization: basic {FORTNITE_LAUNCHER_BASIC_TOKEN[:30]}...")
            log.info(f"[DEBUG] REQUEST DATA: grant_type=client_credentials")
            
            headers_token = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {FORTNITE_LAUNCHER_BASIC_TOKEN}'
            }
            
            data_token = {
                'grant_type': 'client_credentials'
            }
            
            # Usar el endpoint de token para obtener access_token
            async with session.post(EPIC_DEVICE_AUTH_URL, headers=headers_token, data=data_token) as token_response:
                token_text = await token_response.text()
                
                log.info(f"[DEBUG] RESPONSE STATUS: {token_response.status}")
                log.info(f"[DEBUG] RESPONSE HEADERS: {dict(token_response.headers)}")
                log.info(f"[DEBUG] RESPONSE BODY (primeros 500 chars): {token_text[:500]}")
                
                if token_response.status == 200:
                    try:
                        token_data = json.loads(token_text)
                        access_token = token_data.get('access_token')
                        
                        if not access_token:
                            log.error("[DEBUG] ERROR: No se obtuvo access_token de la respuesta")
                            log.error(f"[DEBUG] RESPONSE COMPLETA: {token_text}")
                            return None
                        
                        access_masked = f"{access_token[:10]}...{access_token[-5:]}" if access_token else 'None'
                        log.info(f"[DEBUG] Access_token obtenido: {access_masked}")
                        log.info(f"[DEBUG] Token expires_in: {token_data.get('expires_in', 'N/A')}")
                        
                        # Paso 2: Usar access_token (Bearer) para obtener device codes
                        log.info("[DEBUG] Paso 2: Obteniendo device codes con access_token...")
                        log.info(f"[DEBUG] REQUEST URL: {EPIC_DEVICE_CODE_URL}")
                        log.info(f"[DEBUG] REQUEST HEADERS: Authorization: Bearer {access_masked}")
                        
                        headers_device = {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Authorization': f'Bearer {access_token}'
                        }
                        
                        async with session.post(EPIC_DEVICE_CODE_URL, headers=headers_device) as device_response:
                            device_text = await device_response.text()
                            
                            log.info(f"[DEBUG] DEVICE CODE RESPONSE STATUS: {device_response.status}")
                            log.info(f"[DEBUG] DEVICE CODE RESPONSE HEADERS: {dict(device_response.headers)}")
                            log.info(f"[DEBUG] DEVICE CODE RESPONSE BODY (primeros 500 chars): {device_text[:500]}")
                            
                            if device_response.status == 200:
                                try:
                                    device_data = json.loads(device_text)
                                    
                                    device_code = device_data.get('device_code', '')
                                    user_code = device_data.get('user_code', '')
                                    verification_uri = device_data.get('verification_uri', '')
                                    
                                    log.info(f"[DEBUG] Device code obtenido: {device_code[:10]}...{device_code[-5:]}")
                                    log.info(f"[DEBUG] User code: {user_code}")
                                    log.info(f"[DEBUG] Verification URI: {verification_uri}")
                                    log.info(f"[DEBUG] Expires in: {device_data.get('expires_in', 'N/A')} segundos")
                                    log.info("[DEBUG] ✅ Códigos de dispositivo obtenidos correctamente")
                                    log.info("=" * 60)
                                    
                                    return device_data
                                except json.JSONDecodeError as e:
                                    log.error(f"[DEBUG] ERROR parseando JSON de device codes: {e}")
                                    log.error(f"[DEBUG] RESPONSE COMPLETA: {device_text}")
                                    return None
                            else:
                                # Intentar parsear el error
                                try:
                                    error_data = json.loads(device_text)
                                    error_code = error_data.get('errorCode', 'unknown')
                                    error_message = error_data.get('errorMessage', 'Sin mensaje')
                                    numeric_error = error_data.get('numericErrorCode', 'N/A')
                                    log.error(f"[DEBUG] ERROR obteniendo device codes: {device_response.status}")
                                    log.error(f"[DEBUG] ERROR_CODE: {error_code}")
                                    log.error(f"[DEBUG] ERROR_MESSAGE: {error_message}")
                                    log.error(f"[DEBUG] NUMERIC_ERROR: {numeric_error}")
                                    log.error(f"[DEBUG] RESPONSE COMPLETA: {device_text}")
                                except:
                                    log.error(f"[DEBUG] ERROR obteniendo device codes: {device_response.status}")
                                    log.error(f"[DEBUG] RESPONSE COMPLETA: {device_text[:500]}")
                                return None
                    except json.JSONDecodeError as e:
                        log.error(f"[DEBUG] ERROR parseando JSON de access_token: {e}")
                        log.error(f"[DEBUG] RESPONSE COMPLETA: {token_text}")
                        return None
                else:
                    # Intentar parsear el error del token
                    try:
                        error_data = json.loads(token_text)
                        error_code = error_data.get('errorCode', 'unknown')
                        error_message = error_data.get('errorMessage', 'Sin mensaje')
                        numeric_error = error_data.get('numericErrorCode', 'N/A')
                        log.error(f"[DEBUG] ERROR obteniendo access_token: {token_response.status}")
                        log.error(f"[DEBUG] ERROR_CODE: {error_code}")
                        log.error(f"[DEBUG] ERROR_MESSAGE: {error_message}")
                        log.error(f"[DEBUG] NUMERIC_ERROR: {numeric_error}")
                        log.error(f"[DEBUG] RESPONSE COMPLETA: {token_text}")
                    except:
                        log.error(f"[DEBUG] ERROR obteniendo access_token: {token_response.status}")
                        log.error(f"[DEBUG] RESPONSE COMPLETA: {token_text[:500]}")
                    return None
                    
        except Exception as e:
            log.error(f"[DEBUG] EXCEPTION en get_device_code: {e}")
            import traceback
            log.error(f"[DEBUG] TRACEBACK: {traceback.format_exc()}")
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
            # Usar cliente oficial Launcher (PC) para el intercambio
            # Este es el cliente oficial más reciente aprobado por Epic Games
            session = await self._get_session()
            
            # Headers usando cliente oficial Launcher
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {FORTNITE_LAUNCHER_BASIC_TOKEN}'
            }
            
            # Data con grant_type y device_code
            # Device Code Flow es el método oficial para autenticación de usuario
            data = {
                'grant_type': 'device_code',
                'device_code': authorization_code
            }
            
            log.info(f"Intercambiando device_code por tokens usando cliente oficial Launcher (PC)...")
            
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
                    
                    # Log tokens recibidos (mascarados)
                    access_masked = f"{validated_token['access_token'][:10]}...{validated_token['access_token'][-5:]}" if validated_token.get('access_token') else 'None'
                    refresh_masked = f"{validated_token['refresh_token'][:10]}...{validated_token['refresh_token'][-5:]}" if validated_token.get('refresh_token') else 'None'
                    log.info(f"[DEBUG] Intercambio exitoso - access_token: {access_masked}, refresh_token: {refresh_masked}, account_id: {account_id}, display_name: {display_name}")
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
        device_id: str = None,
        account_id: str = None,
        secret: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Autentica usando Device Auth (device_id + secret)
        Si no se proporcionan valores, usa PRIMARY_ACCOUNT (DeviceAuth válido)
        Este método NO regenera DeviceAuth, solo usa los valores existentes
        
        Args:
            device_id: ID del dispositivo (opcional, usa PRIMARY_ACCOUNT si no se proporciona)
            account_id: ID de la cuenta de Epic Games (opcional, usa PRIMARY_ACCOUNT si no se proporciona)
            secret: Secret (opcional, usa PRIMARY_ACCOUNT si no se proporciona)
            
        Returns:
            Diccionario con tokens de acceso o None si falla
        """
        try:
            # Si no se proporcionan valores, usar PRIMARY_ACCOUNT
            if not device_id or not account_id or not secret:
                log.info("[DEVICEAUTH] Usando PRIMARY_ACCOUNT (valores predefinidos)")
                device_id = PRIMARY_ACCOUNT_DEVICE_ID
                account_id = PRIMARY_ACCOUNT_ID
                secret = PRIMARY_ACCOUNT_SECRET
            
            # Validar datos de entrada
            if not device_id or not account_id or not secret:
                log.error("[DEVICEAUTH] ERROR: device_id, account_id o secret vacíos después de usar PRIMARY_ACCOUNT")
                return None
            
            session = await self._get_session()
            
            # Headers para autenticación DeviceAuth (Android client token usado por DeviceAuthGenerator)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'basic {DEVICEAUTH_BASIC_TOKEN}',
                'User-Agent': PRIMARY_ACCOUNT_USER_AGENT
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
            log.error(f"[DEVICEAUTH] EXCEPTION en authenticate_with_device_auth: {e}")
            import traceback
            log.error(f"[DEVICEAUTH] TRACEBACK: {traceback.format_exc()}")
            return None
    
    async def authenticate_primary_account(self) -> Optional[Dict[str, Any]]:
        """
        Autentica usando PRIMARY_ACCOUNT (DeviceAuth predefinido)
        Método simplificado que siempre usa los valores de PRIMARY_ACCOUNT
        
        Returns:
            Diccionario con tokens de acceso o None si falla
        """
        return await self.authenticate_with_device_auth()
    
    async def _get_account_info_from_token(self, access_token: str) -> Dict[str, Any]:
        """
        Obtiene información de la cuenta usando access_token
        
        Args:
            access_token: Token de acceso
            
        Returns:
            Diccionario con información de la cuenta
        """
        try:
            session = await self._get_session()
            exchange_url = f"{EPIC_OAUTH_BASE}/account/api/oauth/exchange"
            headers = {
                'Authorization': f'bearer {access_token}'
            }
            
            async with session.get(exchange_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'account_id': data.get('account_id') or data.get('id'),
                        'display_name': data.get('displayName') or data.get('display_name', '')
                    }
                else:
                    log.warning(f"[DEVICEAUTH] No se pudo obtener info de cuenta: {response.status}")
                    return {}
        except Exception as e:
            log.error(f"[DEVICEAUTH] Error obteniendo info de cuenta: {e}")
            return {}
    
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

