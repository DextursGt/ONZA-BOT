"""
Módulo de regalos en Fortnite
Permite enviar regalos (items) a otros jugadores
"""

import logging
from typing import Optional, Dict, Any
from .auth import EpicAuth
from .accounts import FortniteAccountManager
from .rate_limiter import get_rate_limiter, get_action_logger
from .tos_validator import get_tos_validator

log = logging.getLogger('fortnite-gifting')

# Base URL de la API de Epic Games para regalos
# NOTA: Esta API puede no estar disponible públicamente
EPIC_GIFTING_API = "https://gift-public-service-prod.ol.epicgames.com/gift/api/public"


class FortniteGifting:
    """Gestiona operaciones de regalos en Fortnite"""
    
    def __init__(self):
        """Inicializa el gestor de regalos"""
        self.auth = EpicAuth()
        self.account_manager = FortniteAccountManager()
        self.rate_limiter = get_rate_limiter()
        self.action_logger = get_action_logger()
        self.tos_validator = get_tos_validator()
        self.gift_message = "¡Disfruta este regalo desde ONZA Bot! 🎁"
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}  # {confirmation_id: gift_data}
    
    async def _get_valid_access_token(self) -> Optional[str]:
        """
        Obtiene un token de acceso válido usando refresh_token
        Siempre obtiene access_token dinámicamente (no se almacena)
        
        Returns:
            Token de acceso válido o None si falla
        """
        try:
            log.info("[DEBUG] [GIFTING] _get_valid_access_token called")
            account = self.account_manager.get_account()
            if not account:
                log.error("[DEBUG] [GIFTING] No hay cuenta activa")
                log.error("No hay cuenta activa - usa !fn_switch para activar una cuenta o !fn_login para agregar una")
                return None
            
            log.info(f"[DEBUG] [GIFTING] Account found - Account #: {account.get('account_number')}, Account ID: {account.get('account_id', 'None')}")
            
            # Obtener refresh_token (único token almacenado)
            encrypted_refresh_token = account.get('encrypted_refresh_token')
            if not encrypted_refresh_token:
                log.error(f"[DEBUG] [GIFTING] No encrypted_refresh_token found")
                log.error(f"No hay refresh_token disponible para cuenta {account.get('account_name', 'desconocida')} - necesitas autenticarte con !fn_login")
                return None
            
            log.info(f"[DEBUG] [GIFTING] Found encrypted_refresh_token (length: {len(encrypted_refresh_token)})")
            
            # Usar DeviceAuth directamente para obtener access_token
            log.info("[DEBUG] [GIFTING] Using DeviceAuth to get access_token...")
            token_data = await self.auth.authenticate_primary_account()
            
            if token_data and token_data.get('access_token'):
                access_masked = f"{token_data['access_token'][:10]}...{token_data['access_token'][-5:]}" if token_data.get('access_token') else 'None'
                log.info(f"[DEBUG] [GIFTING] Access token obtained successfully via DeviceAuth: {access_masked}")
                
                # Guardar refresh_token si viene uno nuevo
                if token_data.get('refresh_token'):
                    log.info("[DEBUG] [GIFTING] New refresh_token received, updating...")
                    encrypted_new_refresh = self.auth.encrypt_token(token_data['refresh_token'])
                    update_success = self.account_manager.update_account_token(
                        account.get('account_number'),
                        encrypted_new_refresh,
                        token_data.get('expires_at')
                    )
                    log.info(f"[DEBUG] [GIFTING] Refresh token updated: {update_success}")
                
                log.info("[DEBUG] [GIFTING] Access_token obtenido correctamente via DeviceAuth")
                return token_data['access_token']
            else:
                log.error("[DEBUG] [GIFTING] DeviceAuth authentication returned None or no access_token")
                log.error("Error obteniendo token con DeviceAuth - verifica los logs del servidor")
                return None
            
        except Exception as e:
            log.error(f"[DEBUG] [GIFTING] Exception in _get_valid_access_token: {e}")
            log.error(f"Error obteniendo token válido: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def set_gift_message(self, message: str):
        """
        Establece el mensaje personalizado para regalos
        
        Args:
            message: Mensaje a incluir con los regalos
        """
        self.gift_message = message
        log.info(f"Mensaje de regalo actualizado: {message}")
    
    def prepare_gift(
        self,
        username: str,
        item_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Prepara un regalo y retorna información para confirmación
        NO envía el regalo todavía
        
        Args:
            username: Nombre de usuario del destinatario
            item_id: ID del item a regalar
            user_id: ID de Discord del usuario
            
        Returns:
            Diccionario con información del regalo y confirmation_id
        """
        import uuid
        
        confirmation_id = str(uuid.uuid4())
        
        gift_info = {
            'confirmation_id': confirmation_id,
            'username': username,
            'item_id': item_id,
            'user_id': user_id,
            'message': self.gift_message,
            'timestamp': None  # Se establecerá al confirmar
        }
        
        self.pending_confirmations[confirmation_id] = gift_info
        
        return {
            'success': True,
            'confirmation_id': confirmation_id,
            'gift_info': gift_info
        }
    
    async def confirm_and_send_gift(
        self,
        confirmation_id: str
    ) -> Dict[str, Any]:
        """
        Confirma y envía un regalo previamente preparado
        
        Args:
            confirmation_id: ID de confirmación del regalo
            
        Returns:
            Diccionario con resultado de la operación
        """
        try:
            # 1. Verificar que existe la confirmación
            if confirmation_id not in self.pending_confirmations:
                return {
                    'success': False,
                    'error': 'Confirmación no encontrada o expirada'
                }
            
            gift_info = self.pending_confirmations[confirmation_id]
            username = gift_info['username']
            item_id = gift_info['item_id']
            user_id = gift_info['user_id']
            
            # 2. Rate limiting y delay natural (muy restrictivo para regalos)
            await self.rate_limiter.wait_if_needed('gift_send')
            
            # 3. Obtener cuenta activa para validación TOS
            account = self.account_manager.get_account()
            if not account:
                del self.pending_confirmations[confirmation_id]
                return {
                    'success': False,
                    'error': 'No hay cuenta activa'
                }
            
            account_id_epic = account.get('account_id')
            
            # 4. Validar TOS (muy importante para regalos)
            tos_valid, tos_error = self.tos_validator.validate_action(
                'gift_send',
                account_id_epic,
                {
                    'item_id': item_id,
                    'recipient': username
                }
            )
            
            if not tos_valid:
                del self.pending_confirmations[confirmation_id]
                self.action_logger.log_action(
                    'gift_send',
                    user_id,
                    {'username': username, 'item_id': item_id},
                    success=False,
                    error=tos_error
                )
                return {
                    'success': False,
                    'error': tos_error or 'Acción no permitida según TOS'
                }
            
            # 5. Obtener token válido
            access_token = await self._get_valid_access_token()
            if not access_token:
                del self.pending_confirmations[confirmation_id]
                self.action_logger.log_action(
                    'gift_send',
                    user_id,
                    {'username': username, 'item_id': item_id},
                    success=False,
                    error='No se pudo obtener token de acceso válido'
                )
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido'
                }
            
            # 6. Obtener account_id del destinatario
            recipient_id = await self._get_account_id_by_username(username, access_token)
            if not recipient_id:
                del self.pending_confirmations[confirmation_id]
                self.action_logger.log_action(
                    'gift_send',
                    user_id,
                    {'username': username, 'item_id': item_id},
                    success=False,
                    error=f'Usuario {username} no encontrado'
                )
                return {
                    'success': False,
                    'error': f'No se encontró el usuario: {username}'
                }
            
            sender_id = account.get('account_id')
            
            # 7. Preparar datos del regalo
            gift_data = {
                'offerId': item_id,
                'recipientId': recipient_id,
                'message': self.gift_message
            }
            
            # 8. Enviar regalo
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{EPIC_GIFTING_API}/gift/{sender_id}"
            
            async with session.post(url, headers=headers, json=gift_data) as response:
                # Eliminar confirmación pendiente
                del self.pending_confirmations[confirmation_id]
                
                if response.status in [200, 201, 204]:
                    # Registrar acción exitosa
                    self.tos_validator.record_action('gift_send', account_id_epic)
                    self.action_logger.log_action(
                        'gift_send',
                        user_id,
                        {
                            'username': username,
                            'item_id': item_id,
                            'recipient_id': recipient_id,
                            'account_id': account_id_epic
                        },
                        success=True
                    )
                    
                    # Delay natural post-acción (más largo para regalos)
                    await self.rate_limiter.apply_natural_delay('gift_send')
                    
                    log.info(f"Regalo enviado a {username} (item: {item_id})")
                    return {
                        'success': True,
                        'message': f'Regalo enviado a {username} correctamente',
                        'item_id': item_id,
                        'recipient': username
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error enviando regalo: {response.status} - {error_text}")
                    
                    # Interpretar errores comunes
                    error_msg = f'Error al enviar regalo: {response.status}'
                    if response.status == 400:
                        error_msg = 'Datos inválidos. Verifica el item_id y el usuario.'
                    elif response.status == 403:
                        error_msg = 'No tienes permisos para enviar este regalo o el item no está disponible.'
                    elif response.status == 404:
                        error_msg = 'La API de regalos no está disponible (404). Epic Games puede haber deshabilitado esta función.'
                    elif response.status == 503 or response.status == 502:
                        error_msg = 'La API de regalos no está disponible temporalmente. Intenta más tarde.'
                    
                    self.action_logger.log_action(
                        'gift_send',
                        user_id,
                        {'username': username, 'item_id': item_id},
                        success=False,
                        error=error_msg
                    )
                    
                    return {
                        'success': False,
                        'error': error_msg
                    }
                    
        except Exception as e:
            log.error(f"Error en confirm_and_send_gift: {e}")
            
            # Obtener user_id antes de eliminar la confirmación
            user_id = 0
            if confirmation_id in self.pending_confirmations:
                user_id = self.pending_confirmations[confirmation_id].get('user_id', 0)
                del self.pending_confirmations[confirmation_id]
            
            self.action_logger.log_action(
                'gift_send',
                user_id,
                {'confirmation_id': confirmation_id},
                success=False,
                error=str(e)
            )
            
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    async def send_gift(
        self, 
        username: str, 
        item_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Usar prepare_gift + confirm_and_send_gift en su lugar
        Envía un regalo directamente (sin confirmación previa)
        
        Args:
            username: Nombre de usuario del destinatario
            item_id: ID del item a regalar
            user_id: ID de Discord del usuario
            
        Returns:
            Diccionario con resultado de la operación
        """
        # Preparar y confirmar inmediatamente (comportamiento antiguo)
        prep_result = self.prepare_gift(username, item_id, user_id)
        if not prep_result['success']:
            return prep_result
        
        return await self.confirm_and_send_gift(prep_result['confirmation_id'])
    
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
    
    async def close(self):
        """Cierra las conexiones"""
        await self.auth.close()

