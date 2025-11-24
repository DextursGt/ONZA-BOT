"""
Módulo de gestión de amigos en Fortnite
Permite agregar y listar amigos usando la API de Epic Games
"""

import aiohttp
import logging
from typing import Optional, List, Dict, Any
from .auth import EpicAuth
from .accounts import FortniteAccountManager
from .rate_limiter import get_rate_limiter, get_action_logger
from .tos_validator import get_tos_validator

log = logging.getLogger('fortnite-friends')

# Base URL de la API de Epic Games para amigos
EPIC_FRIENDS_API = "https://friends-public-service-prod.ol.epicgames.com/friends/api/public"


class FortniteFriends:
    """Gestiona operaciones de amigos en Fortnite"""
    
    def __init__(self):
        """Inicializa el gestor de amigos"""
        self.auth = EpicAuth()
        self.account_manager = FortniteAccountManager()
        self.rate_limiter = get_rate_limiter()
        self.action_logger = get_action_logger()
        self.tos_validator = get_tos_validator()
    
    async def _get_valid_access_token(self) -> Optional[str]:
        """
        Obtiene un token de acceso válido usando refresh_token
        Siempre obtiene access_token dinámicamente (no se almacena)
        
        Returns:
            Token de acceso válido o None si falla
        """
        try:
            account = self.account_manager.get_account()
            if not account:
                log.error("No hay cuenta activa - usa !fn_switch para activar una cuenta o !fn_login para agregar una")
                return None
            
            # Obtener refresh_token (único token almacenado)
            encrypted_refresh_token = account.get('encrypted_refresh_token')
            if not encrypted_refresh_token:
                log.error(f"No hay refresh_token disponible para cuenta {account.get('account_name', 'desconocida')} - necesitas autenticarte con !fn_login")
                return None
            
            # Usar OAuth para refrescar y obtener access_token
            from .oauth import EpicOAuth
            oauth = EpicOAuth()
            
            log.info("Obteniendo access_token usando refresh_token...")
            new_tokens = await oauth.refresh_access_token(encrypted_refresh_token)
            
            if new_tokens and new_tokens.get('access_token'):
                # Actualizar refresh_token si viene uno nuevo
                if new_tokens.get('refresh_token'):
                    encrypted_new_refresh = self.auth.encrypt_token(new_tokens['refresh_token'])
                    self.account_manager.update_account_token(
                        account.get('account_number'),
                        encrypted_new_refresh,
                        new_tokens.get('expires_at')
                    )
                
                log.info("Access_token obtenido correctamente")
                return new_tokens['access_token']
            else:
                log.error("Error refrescando token - el refresh_token puede estar expirado o ser inválido. Usa !fn_login para reautenticarte")
                return None
            
        except Exception as e:
            log.error(f"Error obteniendo token válido: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def add_friend(self, username: str, user_id: int) -> Dict[str, Any]:
        """
        Agrega un amigo por nombre de usuario
        Incluye rate limiting, validación TOS y registro de acciones
        
        Args:
            username: Nombre de usuario de Epic Games
            user_id: ID de Discord del usuario que ejecuta la acción
            
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            # 1. Rate limiting y delay natural
            await self.rate_limiter.wait_if_needed('friend_add')
            
            # 2. Obtener cuenta activa para validación TOS
            account = self.account_manager.get_account()
            if not account:
                return {
                    'success': False,
                    'error': 'No hay cuenta activa'
                }
            
            account_id_epic = account.get('account_id')
            
            # 3. Validar TOS
            tos_valid, tos_error = self.tos_validator.validate_action(
                'friend_add',
                account_id_epic,
                {'username': username}
            )
            
            if not tos_valid:
                self.action_logger.log_action(
                    'friend_add',
                    user_id,
                    {'username': username, 'account_id': account_id_epic},
                    success=False,
                    error=tos_error
                )
                return {
                    'success': False,
                    'error': tos_error or 'Acción no permitida según TOS'
                }
            
            # 4. Obtener token válido
            access_token = await self._get_valid_access_token()
            if not access_token:
                self.action_logger.log_action(
                    'friend_add',
                    user_id,
                    {'username': username},
                    success=False,
                    error='No se pudo obtener token de acceso válido'
                )
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido'
                }
            
            # 5. Obtener account_id del usuario
            target_account_id = await self._get_account_id_by_username(username, access_token)
            if not target_account_id:
                self.action_logger.log_action(
                    'friend_add',
                    user_id,
                    {'username': username},
                    success=False,
                    error=f'Usuario {username} no encontrado'
                )
                return {
                    'success': False,
                    'error': f'No se encontró el usuario: {username}'
                }
            
            # 6. Agregar como amigo
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{EPIC_FRIENDS_API}/friends/{target_account_id}"
            
            async with session.post(url, headers=headers) as response:
                if response.status in [200, 204]:
                    # Registrar acción exitosa
                    self.tos_validator.record_action('friend_add', account_id_epic)
                    self.action_logger.log_action(
                        'friend_add',
                        user_id,
                        {
                            'username': username,
                            'account_id': account_id_epic,
                            'target_account_id': target_account_id
                        },
                        success=True
                    )
                    
                    # Delay natural post-acción
                    await self.rate_limiter.apply_natural_delay('friend_add')
                    
                    log.info(f"Amigo {username} agregado correctamente")
                    return {
                        'success': True,
                        'message': f'Amigo {username} agregado correctamente',
                        'account_id': target_account_id
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error agregando amigo: {response.status} - {error_text}")
                    
                    self.action_logger.log_action(
                        'friend_add',
                        user_id,
                        {'username': username},
                        success=False,
                        error=f'HTTP {response.status}: {error_text}'
                    )
                    
                    return {
                        'success': False,
                        'error': f'Error al agregar amigo: {response.status}'
                    }
                    
        except Exception as e:
            log.error(f"Error en add_friend: {e}")
            self.action_logger.log_action(
                'friend_add',
                user_id,
                {'username': username},
                success=False,
                error=str(e)
            )
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    async def _get_account_id_by_username(
        self, 
        username: str, 
        access_token: str
    ) -> Optional[str]:
        """
        Obtiene el account_id de Epic Games por nombre de usuario
        
        Args:
            username: Nombre de usuario
            access_token: Token de acceso
            
        Returns:
            Account ID o None si no se encuentra
        """
        try:
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Endpoint de búsqueda de usuarios
            url = f"https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/displayName/{username}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('id')
                else:
                    log.warning(f"Usuario {username} no encontrado: {response.status}")
                    return None
                    
        except Exception as e:
            log.error(f"Error obteniendo account_id: {e}")
            return None
    
    async def list_friends(self, user_id: int) -> Dict[str, Any]:
        """
        Lista todos los amigos de la cuenta activa
        Incluye rate limiting y registro de acciones
        
        Args:
            user_id: ID de Discord del usuario que ejecuta la acción
            
        Returns:
            Diccionario con lista de amigos o error
        """
        try:
            # 1. Rate limiting y delay natural
            await self.rate_limiter.wait_if_needed('friend_list')
            
            # 2. Obtener token válido
            access_token = await self._get_valid_access_token()
            if not access_token:
                self.action_logger.log_action(
                    'friend_list',
                    user_id,
                    {},
                    success=False,
                    error='No se pudo obtener token de acceso válido'
                )
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido',
                    'friends': []
                }
            
            # 3. Obtener account_id de la cuenta activa
            account = self.account_manager.get_account()
            if not account:
                return {
                    'success': False,
                    'error': 'No hay cuenta activa',
                    'friends': []
                }
            
            account_id = account.get('account_id')
            
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            url = f"{EPIC_FRIENDS_API}/friends/{account_id}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    friends_data = await response.json()
                    
                    # Procesar lista de amigos
                    friends_list = []
                    for friend in friends_data:
                        friends_list.append({
                            'account_id': friend.get('accountId'),
                            'display_name': friend.get('displayName', 'Unknown'),
                            'status': friend.get('status', 'unknown'),
                            'favorite': friend.get('favorite', False)
                        })
                    
                    # Registrar acción exitosa
                    self.action_logger.log_action(
                        'friend_list',
                        user_id,
                        {'account_id': account_id, 'count': len(friends_list)},
                        success=True
                    )
                    
                    # Delay natural post-acción
                    await self.rate_limiter.apply_natural_delay('friend_list')
                    
                    log.info(f"Listados {len(friends_list)} amigos")
                    return {
                        'success': True,
                        'friends': friends_list,
                        'count': len(friends_list)
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error listando amigos: {response.status} - {error_text}")
                    
                    self.action_logger.log_action(
                        'friend_list',
                        user_id,
                        {},
                        success=False,
                        error=f'HTTP {response.status}'
                    )
                    
                    return {
                        'success': False,
                        'error': f'Error al listar amigos: {response.status}',
                        'friends': []
                    }
                    
        except Exception as e:
            log.error(f"Error en list_friends: {e}")
            self.action_logger.log_action(
                'friend_list',
                user_id,
                {},
                success=False,
                error=str(e)
            )
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}',
                'friends': []
            }
    
    async def close(self):
        """Cierra las conexiones"""
        await self.auth.close()

