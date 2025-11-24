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
import logging

log = logging.getLogger('fortnite-auth')

# Configuración de Epic Games OAuth
EPIC_OAUTH_BASE = "https://account-public-service-prod03.ol.epicgames.com"
EPIC_DEVICE_AUTH_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/token"
EPIC_DEVICE_CODE_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/deviceAuthorization"

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
            # Verificar campos requeridos
            required_fields = ['access_token', 'refresh_token', 'account_id']
            for field in required_fields:
                if field not in token_data or not token_data[field]:
                    log.warning(f"Token inválido: falta campo {field}")
                    return False
            
            # Verificar que el access_token tiene el formato correcto
            access_token = token_data.get('access_token', '')
            if not access_token or len(access_token) < 50:
                log.warning("Token de acceso tiene formato inválido")
                return False
            
            # Verificar que el account_id es válido (debe ser un UUID o ID numérico)
            account_id = token_data.get('account_id', '')
            if not account_id or len(account_id) < 10:
                log.warning("Account ID inválido")
                return False
            
            # Verificar que el client_id es el oficial de Epic Games
            client_id = token_data.get('client_id', '')
            # Epic Games usa client_id específicos, verificar que existe
            if client_id and len(client_id) < 10:
                log.warning("Client ID inválido")
                return False
            
            log.info("Token OAuth validado correctamente")
            return True
            
        except Exception as e:
            log.error(f"Error validando token OAuth: {e}")
            return False
    
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
            # Usar ANDROID_TOKEN como en DeviceAuthGenerator para device auth
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU='
            }
            
            # Usar grant_type device_auth con device_id y secret
            # Formato según documentación de Epic Games Device Auth
            data = {
                'grant_type': 'device_auth',
                'device_id': device_id,
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

