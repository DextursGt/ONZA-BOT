"""
Módulo OAuth oficial de Epic Games con PKCE
Maneja autenticación OAuth 2.0 Authorization Code Flow con PKCE
NO usa client_secret ni client_credentials
Solo almacena refresh_token encriptado
"""

import os
import secrets
import hashlib
import base64
import aiohttp
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs, urlparse
import logging

from .auth import EpicAuth, TokenEncryption

log = logging.getLogger('fortnite-oauth')

# Configuración OAuth de Epic Games
EPIC_OAUTH_BASE = "https://account-public-service-prod03.ol.epicgames.com"
EPIC_OAUTH_AUTHORIZE_URL = "https://www.epicgames.com/id/authorize"
EPIC_OAUTH_TOKEN_URL = f"{EPIC_OAUTH_BASE}/account/api/oauth/token"

# Client ID de Epic Games - Cliente Oficial Launcher (PC)
# Este es el cliente oficial aprobado por Epic Games
# NO usamos client_secret - PKCE elimina la necesidad de client_secret
EPIC_CLIENT_ID = "34a02cf8f4414e29b15921876da368da"

# Redirect URI - URL local para capturar el callback
# El usuario copiará el código de la URL después de autorizar
EPIC_REDIRECT_URI = "http://localhost:4000/callback"

# Scopes necesarios para Fortnite - Scopes oficiales y modernos
EPIC_SCOPES = [
    "basic_profile",      # Información básica del perfil
    "friends_list",      # Lista de amigos
    "presence",          # Estado de presencia
    "openid",            # OpenID Connect
    "offline_access"     # Necesario para obtener refresh_token
]


class EpicOAuth:
    """
    Maneja autenticación OAuth oficial de Epic Games con PKCE
    Usa Authorization Code Flow con PKCE (sin client_secret)
    """
    
    def __init__(self):
        """Inicializa el gestor OAuth"""
        self.auth = EpicAuth()
        self.pending_authorizations: Dict[str, Dict[str, Any]] = {}
        # Almacenar autorizaciones pendientes: {state: {user_id, code_verifier, timestamp, expires_at}}
    
    def _generate_code_verifier(self) -> str:
        """
        Genera un code_verifier seguro para PKCE
        Debe ser una cadena URL-safe aleatoria de 43-128 caracteres
        
        Returns:
            Code verifier en formato base64url
        """
        # Generar 32 bytes aleatorios (256 bits)
        # Base64url de 32 bytes = 43 caracteres (perfecto para PKCE)
        random_bytes = secrets.token_bytes(32)
        code_verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
        return code_verifier
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """
        Genera code_challenge usando SHA256 del code_verifier (método S256)
        
        Args:
            code_verifier: El code verifier generado
            
        Returns:
            Code challenge en formato base64url
        """
        # SHA256 del code_verifier
        sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        # Base64url encode
        code_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
        return code_challenge
    
    def generate_login_url(self, user_id: int) -> Tuple[str, str, str]:
        """
        Genera URL de login OAuth de Epic Games con PKCE
        
        Args:
            user_id: ID de Discord del usuario que solicita login
            
        Returns:
            Tupla con (login_url, state_code, code_verifier)
        """
        # Generar state único para prevenir CSRF
        state = secrets.token_urlsafe(32)
        
        # Generar code_verifier y code_challenge para PKCE
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        
        log.info(f"[DEBUG] PKCE generado - code_verifier: {code_verifier[:10]}...{code_verifier[-5:]}")
        log.info(f"[DEBUG] PKCE generado - code_challenge: {code_challenge[:10]}...{code_challenge[-5:]}")
        
        # Parámetros OAuth con PKCE
        params = {
            'client_id': EPIC_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': EPIC_REDIRECT_URI,
            'scope': ' '.join(EPIC_SCOPES),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',  # SHA256
            'prompt': 'login'  # Forzar login
        }
        
        # Construir URL
        login_url = f"{EPIC_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
        
        # Logs detallados
        log.info(f"[DEBUG] AUTH URL generada: {login_url[:100]}...")
        log.info(f"[DEBUG] REQUESTED CLIENT: {EPIC_CLIENT_ID}")
        log.info(f"[DEBUG] REQUESTED SCOPE: {' '.join(EPIC_SCOPES)}")
        log.info(f"[DEBUG] REDIRECT: {EPIC_REDIRECT_URI}")
        log.info(f"[DEBUG] CODE_CHALLENGE_METHOD: S256")
        
        # Guardar autorización pendiente con code_verifier (expira en 10 minutos)
        self.pending_authorizations[state] = {
            'user_id': user_id,
            'code_verifier': code_verifier,
            'code_challenge': code_challenge,
            'timestamp': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        log.info(f"URL de login OAuth con PKCE generada para usuario {user_id}, state: {state[:10]}...")
        
        return login_url, state, code_verifier
    
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
    
    def get_code_verifier(self, state: str) -> Optional[str]:
        """
        Obtiene el code_verifier asociado a un state
        
        Args:
            state: State code de la autorización
            
        Returns:
            Code verifier o None si no existe
        """
        if state in self.pending_authorizations:
            return self.pending_authorizations[state].get('code_verifier')
        return None
    
    async def exchange_code_for_tokens(self, authorization_code: str, state: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Intercambia código de autorización por tokens OAuth usando PKCE
        NO usa client_secret - solo client_id y code_verifier
        
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
        
        # Obtener code_verifier asociado al state
        code_verifier = self.get_code_verifier(state)
        if not code_verifier:
            log.error(f"Code verifier no encontrado para state {state[:10]}...")
            return None
        
        try:
            # Crear sesión HTTP
            async with aiohttp.ClientSession() as session:
                # Headers para intercambio de código (SIN Authorization básica - PKCE no la requiere)
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Datos para intercambio con PKCE
                # NO incluimos client_secret - PKCE elimina esa necesidad
                data = {
                    'grant_type': 'authorization_code',
                    'code': authorization_code,
                    'client_id': EPIC_CLIENT_ID,
                    'code_verifier': code_verifier,
                    'redirect_uri': EPIC_REDIRECT_URI
                }
                
                log.info(f"[DEBUG] Intercambiando código por tokens con PKCE para usuario {user_id}...")
                log.info(f"[DEBUG] REQUEST URL: {EPIC_OAUTH_TOKEN_URL}")
                log.info(f"[DEBUG] REQUEST DATA: grant_type=authorization_code, client_id={EPIC_CLIENT_ID}, redirect_uri={EPIC_REDIRECT_URI}")
                log.info(f"[DEBUG] CODE_VERIFIER usado: {code_verifier[:10]}...{code_verifier[-5:]}")
                
                async with session.post(EPIC_OAUTH_TOKEN_URL, headers=headers, data=data) as response:
                    response_text = await response.text()
                    
                    log.info(f"[DEBUG] RESPONSE STATUS: {response.status}")
                    log.info(f"[DEBUG] RESPONSE BODY (primeros 500 chars): {response_text[:500]}")
                    
                    if response.status == 200:
                        try:
                            token_data = await response.json()
                        except Exception as json_error:
                            log.error(f"[DEBUG] Error parseando JSON: {json_error} - {response_text}")
                            return None
                        
                        # Validar respuesta
                        if 'access_token' not in token_data or 'refresh_token' not in token_data:
                            log.error("[DEBUG] Respuesta de tokens incompleta")
                            log.error(f"[DEBUG] RESPONSE COMPLETA: {response_text}")
                            return None
                        
                        # Logs de tokens recibidos (mascarados)
                        access_masked = f"{token_data['access_token'][:10]}...{token_data['access_token'][-5:]}" if token_data.get('access_token') else 'None'
                        refresh_masked = f"{token_data['refresh_token'][:10]}...{token_data['refresh_token'][-5:]}" if token_data.get('refresh_token') else 'None'
                        log.info(f"[DEBUG] Tokens recibidos - access_token: {access_masked}, refresh_token: {refresh_masked}")
                        
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
                            'source': 'epic_oauth_pkce'
                        }
                        
                        log.info(f"[DEBUG] ✅ Tokens obtenidos exitosamente - account_id: {result.get('account_id', 'N/A')}")
                        log.info(f"Tokens obtenidos exitosamente para usuario {user_id}, account_id: {result.get('account_id', 'N/A')}")
                        return result
                    else:
                        # Intentar parsear el error
                        try:
                            error_data = json.loads(response_text)
                            error_code = error_data.get('errorCode', 'unknown')
                            error_message = error_data.get('errorMessage', 'Sin mensaje')
                            log.error(f"[DEBUG] ERROR_CODE: {error_code}")
                            log.error(f"[DEBUG] ERROR_MESSAGE: {error_message}")
                        except:
                            pass
                        log.error(f"[DEBUG] Error intercambiando código: {response.status} - {response_text[:500]}")
                        return None
                        
        except Exception as e:
            log.error(f"[DEBUG] EXCEPTION en exchange_code_for_tokens: {e}")
            import traceback
            log.error(f"[DEBUG] TRACEBACK: {traceback.format_exc()}")
            log.error(f"Error en exchange_code_for_tokens: {e}")
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
    
    async def refresh_access_token(self, encrypted_refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Renueva access_token usando refresh_token
        NO usa client_secret - solo client_id y refresh_token (PKCE)
        
        Args:
            encrypted_refresh_token: Refresh token encriptado
            
        Returns:
            Nuevo access_token o None si falla
        """
        try:
            # Descifrar refresh token usando TokenEncryption
            decrypted_refresh = self.auth.encryption.decrypt_token(encrypted_refresh_token)
            
            # Crear sesión HTTP
            async with aiohttp.ClientSession() as session:
                # Headers SIN Authorization básica - PKCE no requiere client_secret
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                
                # Datos para refresh - SOLO grant_type, refresh_token y client_id
                # NO incluimos client_secret
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': decrypted_refresh,
                    'client_id': EPIC_CLIENT_ID
                }
                
                log.info(f"[DEBUG] Refreshing access_token con PKCE (sin client_secret)...")
                log.info(f"[DEBUG] REQUEST URL: {EPIC_OAUTH_TOKEN_URL}")
                log.info(f"[DEBUG] REQUEST DATA: grant_type=refresh_token, client_id={EPIC_CLIENT_ID}")
                log.info(f"[DEBUG] Using refresh_token: {decrypted_refresh[:10]}...{decrypted_refresh[-5:]}")
                
                async with session.post(EPIC_OAUTH_TOKEN_URL, headers=headers, data=data) as response:
                    response_text = await response.text()
                    
                    log.info(f"[DEBUG] RESPONSE STATUS: {response.status}")
                    log.info(f"[DEBUG] RESPONSE BODY (primeros 500 chars): {response_text[:500]}")
                    
                    if response.status == 200:
                        try:
                            token_data = await response.json()
                        except Exception as json_error:
                            log.error(f"[DEBUG] Error parseando JSON: {json_error} - {response_text}")
                            return None
                        
                        access_masked = f"{token_data.get('access_token', '')[:10]}...{token_data.get('access_token', '')[-5:]}" if token_data.get('access_token') else 'None'
                        refresh_masked = f"{token_data.get('refresh_token', '')[:10]}...{token_data.get('refresh_token', '')[-5:]}" if token_data.get('refresh_token') else 'None'
                        log.info(f"[DEBUG] Token refresh successful - access_token: {access_masked}, refresh_token: {refresh_masked}")
                        
                        expires_in = token_data.get('expires_in', 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        log.info(f"[DEBUG] Token expires in: {expires_in} seconds, at: {expires_at.isoformat()}")
                        
                        result = {
                            'access_token': token_data.get('access_token'),
                            'refresh_token': token_data.get('refresh_token', decrypted_refresh),  # Puede venir nuevo refresh_token
                            'expires_at': expires_at.isoformat(),
                            'token_type': token_data.get('token_type', 'Bearer')
                        }
                        log.info(f"[DEBUG] Returning token data - has access_token: {bool(result.get('access_token'))}, has refresh_token: {bool(result.get('refresh_token'))}")
                        return result
                    else:
                        # Intentar parsear el error
                        try:
                            error_data = json.loads(response_text)
                            error_code = error_data.get('errorCode', 'unknown')
                            error_message = error_data.get('errorMessage', 'Sin mensaje')
                            log.error(f"[DEBUG] ERROR_CODE: {error_code}")
                            log.error(f"[DEBUG] ERROR_MESSAGE: {error_message}")
                        except:
                            pass
                        log.error(f"[DEBUG] Token refresh failed - Status: {response.status}, Error: {response_text[:500]}")
                        log.error(f"Error refrescando token: {response.status} - {response_text[:500]}")
                        return None
                        
        except Exception as e:
            log.error(f"[DEBUG] EXCEPTION en refresh_access_token: {e}")
            import traceback
            log.error(f"[DEBUG] TRACEBACK: {traceback.format_exc()}")
            log.error(f"Error en refresh_access_token: {e}")
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

