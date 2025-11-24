"""
Módulo OAuth oficial de Epic Games
Maneja autenticación OAuth 2.0 sin DeviceAuth ni contraseñas
Solo almacena refresh_token encriptado
"""

import os
import secrets
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
import logging

from .auth import EpicAuth, TokenEncryption

log = logging.getLogger('fortnite-oauth')

# Configuración OAuth de Epic Games
EPIC_OAUTH_BASE = "https://account-public-service-prod03.ol.epicgames.com"
EPIC_OAUTH_AUTHORIZE_URL = "https://www.epicgames.com/id/authorize"
EPIC_OAUTH_TOKEN_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/token"

# Client ID y Secret de Epic Games (públicos para OAuth)
# Estos son los clientes oficiales de Epic Games
EPIC_CLIENT_ID = "3f69e56c749492c8cc29f1af08aa12e"
EPIC_CLIENT_SECRET = "b51ee9cb12234f50a69efa67ef53812e"

# Redirect URI (debe coincidir con el registrado en Epic Games)
# Para bots de Discord, usamos un URI local que el usuario copiará
EPIC_REDIRECT_URI = "https://www.epicgames.com/id/api/redirect"

# Scopes necesarios para Fortnite
EPIC_SCOPES = [
    "basic_profile",
    "friends_list",
    "presence",
    "openid",
    "offline_access"  # Necesario para obtener refresh_token
]


class EpicOAuth:
    """
    Maneja autenticación OAuth oficial de Epic Games
    Genera enlaces de login y procesa callbacks
    """
    
    def __init__(self):
        """Inicializa el gestor OAuth"""
        self.auth = EpicAuth()
        self.pending_authorizations: Dict[str, Dict[str, Any]] = {}
        # Almacenar autorizaciones pendientes: {state: {user_id, timestamp, expires_at}}
    
    def generate_login_url(self, user_id: int) -> tuple[str, str]:
        """
        Genera URL de login OAuth de Epic Games
        
        Args:
            user_id: ID de Discord del usuario que solicita login
            
        Returns:
            Tupla con (login_url, state_code)
        """
        # Generar state único para prevenir CSRF
        state = secrets.token_urlsafe(32)
        
        # Parámetros OAuth
        params = {
            'client_id': EPIC_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': EPIC_REDIRECT_URI,
            'scope': ' '.join(EPIC_SCOPES),
            'state': state,
            'prompt': 'login'  # Forzar login
        }
        
        # Construir URL
        login_url = f"{EPIC_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
        
        # Guardar autorización pendiente (expira en 10 minutos)
        self.pending_authorizations[state] = {
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        log.info(f"URL de login OAuth generada para usuario {user_id}, state: {state[:10]}...")
        
        return login_url, state
    
    def _cleanup_expired_authorizations(self):
        """Elimina autorizaciones expiradas"""
        now = datetime.utcnow()
        expired_states = [
            state for state, data in self.pending_authorizations.items()
            if data['expires_at'] < now
        ]
        for state in expired_states:
            del self.pending_authorizations[state]
            log.debug(f"Autorización expirada eliminada: {state[:10]}...")
    
    def validate_state(self, state: str, user_id: int) -> bool:
        """
        Valida que el state corresponde al usuario
        
        Args:
            state: State code de la autorización
            user_id: ID de Discord del usuario
            
        Returns:
            True si el state es válido, False en caso contrario
        """
        self._cleanup_expired_authorizations()
        
        if state not in self.pending_authorizations:
            log.warning(f"State no encontrado: {state[:10]}...")
            return False
        
        auth_data = self.pending_authorizations[state]
        
        # Verificar que no haya expirado
        if auth_data['expires_at'] < datetime.utcnow():
            log.warning(f"State expirado: {state[:10]}...")
            del self.pending_authorizations[state]
            return False
        
        # Verificar que corresponde al usuario correcto
        if auth_data['user_id'] != user_id:
            log.warning(f"State no corresponde al usuario: {state[:10]}... (esperado: {auth_data['user_id']}, recibido: {user_id})")
            return False
        
        return True
    
    async def exchange_code_for_tokens(self, authorization_code: str, state: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Intercambia código de autorización por tokens OAuth
        
        Args:
            authorization_code: Código recibido del callback de Epic Games
            state: State code para validar la solicitud
            user_id: ID de Discord del usuario
            
        Returns:
            Diccionario con tokens o None si falla
        """
        # Validar state
        if not self.validate_state(state, user_id):
            log.error(f"State inválido para usuario {user_id}")
            return None
        
        try:
            # Crear sesión HTTP
            async with aiohttp.ClientSession() as session:
                # Headers para intercambio de código
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'basic {self._get_basic_auth_header()}'
                }
                
                # Datos para intercambio
                data = {
                    'grant_type': 'authorization_code',
                    'code': authorization_code,
                    'redirect_uri': EPIC_REDIRECT_URI
                }
                
                log.info(f"Intercambiando código por tokens para usuario {user_id}...")
                
                async with session.post(EPIC_OAUTH_TOKEN_URL, headers=headers, data=data) as response:
                    if response.status == 200:
                        try:
                            token_data = await response.json()
                        except Exception as json_error:
                            response_text = await response.text()
                            log.error(f"Error parseando JSON: {json_error} - {response_text}")
                            return None
                        
                        # Validar respuesta
                        if 'access_token' not in token_data or 'refresh_token' not in token_data:
                            log.error("Respuesta de tokens incompleta")
                            return None
                        
                        # Calcular tiempo de expiración
                        expires_in = token_data.get('expires_in', 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        
                        # Obtener información de la cuenta
                        account_info = await self._get_account_info(token_data['access_token'], session)
                        
                        # Limpiar autorización pendiente
                        if state in self.pending_authorizations:
                            del self.pending_authorizations[state]
                        
                        result = {
                            'access_token': token_data['access_token'],
                            'refresh_token': token_data['refresh_token'],
                            'expires_at': expires_at.isoformat(),
                            'account_id': token_data.get('account_id') or account_info.get('account_id', ''),
                            'display_name': account_info.get('display_name', ''),
                            'token_type': token_data.get('token_type', 'Bearer'),
                            'source': 'epic_oauth_official'
                        }
                        
                        log.info(f"Tokens obtenidos exitosamente para usuario {user_id}, account_id: {result.get('account_id', 'N/A')}")
                        return result
                    else:
                        error_text = await response.text()
                        log.error(f"Error intercambiando código: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            log.error(f"Error en exchange_code_for_tokens: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def _get_account_info(self, access_token: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Obtiene información de la cuenta usando el access token
        
        Args:
            access_token: Token de acceso
            session: Sesión HTTP existente
            
        Returns:
            Diccionario con información de la cuenta
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Obtener información básica de la cuenta
            url = f"{EPIC_OAUTH_BASE}/account/api/oauth/verify"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'account_id': data.get('account_id', ''),
                        'display_name': data.get('displayName', ''),
                        'email': data.get('email', '')  # No lo guardamos, solo para verificación
                    }
                else:
                    log.warning(f"Error obteniendo info de cuenta: {response.status}")
                    return {}
        except Exception as e:
            log.error(f"Error en _get_account_info: {e}")
            return {}
    
    def _get_basic_auth_header(self) -> str:
        """
        Genera header de autenticación básica para OAuth
        Usa el token básico que funciona según el código de referencia
        
        Returns:
            String con credenciales en base64
        """
        # Usar el token básico que funciona (del código de referencia)
        return EPIC_OAUTH_BASIC_TOKEN
    
    async def refresh_access_token(self, encrypted_refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Renueva access_token usando refresh_token
        
        Args:
            encrypted_refresh_token: Refresh token encriptado
            
        Returns:
            Nuevo access_token o None si falla
        """
        try:
            # Descifrar refresh token
            decrypted_refresh = self.auth.decrypt_token(encrypted_refresh_token)
            
            # Crear sesión HTTP
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': f'basic {self._get_basic_auth_header()}'
                }
                
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': decrypted_refresh
                }
                
                async with session.post(EPIC_OAUTH_TOKEN_URL, headers=headers, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        
                        expires_in = token_data.get('expires_in', 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        
                        return {
                            'access_token': token_data.get('access_token'),
                            'refresh_token': token_data.get('refresh_token', decrypted_refresh),  # Puede venir nuevo refresh_token
                            'expires_at': expires_at.isoformat(),
                            'token_type': token_data.get('token_type', 'Bearer')
                        }
                    else:
                        error_text = await response.text()
                        log.error(f"Error refrescando token: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            log.error(f"Error en refresh_access_token: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def extract_code_from_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extrae código y state de una URL de callback de Epic Games
        
        Args:
            url: URL completa del callback
            
        Returns:
            Tupla con (authorization_code, state) o (None, None) si no se encuentra
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            code = params.get('code', [None])[0]
            state = params.get('state', [None])[0]
            
            # También verificar fragment (#) por si Epic Games lo envía ahí
            if not code and parsed.fragment:
                fragment_params = parse_qs(parsed.fragment)
                code = fragment_params.get('code', [None])[0]
                state = fragment_params.get('state', [None])[0]
            
            return code, state
        except Exception as e:
            log.error(f"Error extrayendo código de URL: {e}")
            return None, None

