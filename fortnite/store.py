"""
Módulo de tienda de Fortnite
Permite ver items, precios, rareza y rotación de la tienda
"""

import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .auth import EpicAuth
from .accounts import FortniteAccountManager
from .rate_limiter import get_rate_limiter, get_action_logger
from .tos_validator import get_tos_validator

log = logging.getLogger('fortnite-store')

# Base URL de la API de Epic Games para la tienda
EPIC_CATALOG_API = "https://catalog-public-service-prod.ol.epicgames.com/catalog/api/shared"


class FortniteStore:
    """Gestiona operaciones de la tienda de Fortnite"""
    
    def __init__(self):
        """Inicializa el gestor de tienda"""
        self.auth = EpicAuth()
        self.account_manager = FortniteAccountManager()
        self.rate_limiter = get_rate_limiter()
        self.action_logger = get_action_logger()
        self.tos_validator = get_tos_validator()
        self.cache: Optional[Dict[str, Any]] = None
        self.cache_time: Optional[datetime] = None
        self.cache_duration = 3600  # 1 hora en segundos
    
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
                log.error("No hay cuenta activa")
                return None
            
            # Obtener refresh_token (único token almacenado)
            encrypted_refresh_token = account.get('encrypted_refresh_token')
            if not encrypted_refresh_token:
                log.error("No hay refresh_token disponible")
                return None
            
            # Usar OAuth para refrescar y obtener access_token
            from .oauth import EpicOAuth
            oauth = EpicOAuth()
            
            log.debug("Obteniendo access_token usando refresh_token...")
            new_tokens = await oauth.refresh_access_token(encrypted_refresh_token)
            
            if new_tokens:
                # Actualizar refresh_token si viene uno nuevo
                if new_tokens.get('refresh_token'):
                    encrypted_new_refresh = self.auth.encrypt_token(new_tokens['refresh_token'])
                    self.account_manager.update_account_token(
                        account.get('account_number'),
                        encrypted_new_refresh,
                        new_tokens.get('expires_at')
                    )
                
                return new_tokens['access_token']
            else:
                log.error("Error refrescando token")
                return None
            
        except Exception as e:
            log.error(f"Error obteniendo token válido: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _is_cache_valid(self) -> bool:
        """
        Verifica si el caché de la tienda es válido
        
        Returns:
            True si el caché es válido, False en caso contrario
        """
        if self.cache is None or self.cache_time is None:
            return False
        
        elapsed = (datetime.utcnow() - self.cache_time).total_seconds()
        return elapsed < self.cache_duration
    
    async def get_store(self, use_cache: bool = True, user_id: int = 0) -> Dict[str, Any]:
        """
        Obtiene los items de la tienda actual
        
        Args:
            use_cache: Si usar caché si está disponible
            
        Returns:
            Diccionario con items de la tienda o error
        """
        try:
            # 1. Verificar caché (evita llamadas API innecesarias)
            if use_cache and self._is_cache_valid():
                log.info("Usando datos en caché de la tienda")
                self.action_logger.log_action(
                    'store_get',
                    user_id,
                    {'cached': True},
                    success=True
                )
                return {
                    'success': True,
                    'items': self.cache.get('items', []),
                    'cached': True
                }
            
            # 2. Rate limiting y delay natural
            await self.rate_limiter.wait_if_needed('store_get')
            
            # 3. Obtener token válido
            access_token = await self._get_valid_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido',
                    'items': []
                }
            
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Endpoint para obtener la tienda
            # Nota: La API exacta puede variar, esto es una aproximación
            url = f"{EPIC_CATALOG_API}/namespace/fn/storefront"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    store_data = await response.json()
                    
                    # Procesar items de la tienda
                    items = self._process_store_items(store_data)
                    
                    # Actualizar caché
                    self.cache = {'items': items}
                    self.cache_time = datetime.utcnow()
                    
                    # Registrar acción exitosa
                    self.action_logger.log_action(
                        'store_get',
                        user_id,
                        {'count': len(items)},
                        success=True
                    )
                    
                    # Delay natural post-acción
                    await self.rate_limiter.apply_natural_delay('store_get')
                    
                    log.info(f"Tienda obtenida: {len(items)} items")
                    return {
                        'success': True,
                        'items': items,
                        'cached': False,
                        'count': len(items)
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error obteniendo tienda: {response.status} - {error_text}")
                    
                    # Intentar con endpoint alternativo (Fortnite API pública)
                    return await self._get_store_fallback()
                    
        except Exception as e:
            log.error(f"Error en get_store: {e}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}',
                'items': []
            }
    
    async def _get_store_fallback(self) -> Dict[str, Any]:
        """
        Método alternativo para obtener la tienda usando API pública
        
        Returns:
            Diccionario con items de la tienda
        """
        try:
            # Usar API pública de Fortnite como fallback
            session = await self.auth._get_session()
            url = "https://fortnite-api.com/v2/shop/br"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    items = self._process_fortnite_api_items(data)
                    
                    self.cache = {'items': items}
                    self.cache_time = datetime.utcnow()
                    
                    return {
                        'success': True,
                        'items': items,
                        'cached': False,
                        'count': len(items),
                        'source': 'fortnite-api.com'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No se pudo obtener la tienda',
                        'items': []
                    }
        except Exception as e:
            log.error(f"Error en fallback: {e}")
            return {
                'success': False,
                'error': f'Error obteniendo tienda: {str(e)}',
                'items': []
            }
    
    def _process_store_items(self, store_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Procesa los datos de la tienda y extrae items
        
        Args:
            store_data: Datos brutos de la API
            
        Returns:
            Lista de items procesados
        """
        items = []
        
        try:
            # Estructura puede variar según la API
            storefront = store_data.get('storefront', {})
            featured = storefront.get('featured', {})
            daily = storefront.get('daily', {})
            
            # Procesar items destacados
            for item in featured.get('entries', []):
                items.append(self._process_item(item))
            
            # Procesar items diarios
            for item in daily.get('entries', []):
                items.append(self._process_item(item))
                
        except Exception as e:
            log.error(f"Error procesando items: {e}")
        
        return items
    
    def _process_fortnite_api_items(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Procesa items de la API pública de Fortnite
        
        Args:
            api_data: Datos de la API pública
            
        Returns:
            Lista de items procesados
        """
        items = []
        
        try:
            shop_data = api_data.get('data', {}).get('featured', {}).get('entries', [])
            shop_data.extend(api_data.get('data', {}).get('daily', {}).get('entries', []))
            
            for entry in shop_data:
                item_data = {
                    'item_id': entry.get('offerId'),
                    'name': entry.get('bundle', {}).get('name') or entry.get('items', [{}])[0].get('name', 'Unknown'),
                    'price': entry.get('finalPrice', 0),
                    'original_price': entry.get('regularPrice', 0),
                    'rarity': entry.get('items', [{}])[0].get('rarity', {}).get('value', 'common'),
                    'type': entry.get('items', [{}])[0].get('type', {}).get('value', 'unknown'),
                    'image_url': entry.get('newDisplayAsset', {}).get('materialInstances', [{}])[0].get('images', {}).get('Background', ''),
                    'is_featured': entry.get('section', {}).get('id') == 'featured'
                }
                items.append(item_data)
                
        except Exception as e:
            log.error(f"Error procesando items de API pública: {e}")
        
        return items
    
    def _process_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un item individual de la tienda
        
        Args:
            item_data: Datos del item
            
        Returns:
            Diccionario con información del item
        """
        return {
            'item_id': item_data.get('offerId') or item_data.get('id'),
            'name': item_data.get('title') or item_data.get('name', 'Unknown'),
            'price': item_data.get('price', {}).get('finalPrice', 0) if isinstance(item_data.get('price'), dict) else item_data.get('price', 0),
            'original_price': item_data.get('price', {}).get('regularPrice', 0) if isinstance(item_data.get('price'), dict) else item_data.get('price', 0),
            'rarity': item_data.get('rarity', 'common'),
            'type': item_data.get('type', 'unknown'),
            'image_url': item_data.get('imageUrl') or item_data.get('image', ''),
            'description': item_data.get('description', '')
        }
    
    async def get_item_info(self, item_id: str, user_id: int = 0) -> Dict[str, Any]:
        """
        Obtiene información detallada de un item específico
        
        Args:
            item_id: ID del item
            
        Returns:
            Diccionario con información del item o error
        """
        try:
            # 1. Rate limiting y delay natural
            await self.rate_limiter.wait_if_needed('item_info')
            
            # 2. Obtener token válido
            access_token = await self._get_valid_access_token()
            if not access_token:
                self.action_logger.log_action(
                    'item_info',
                    user_id,
                    {'item_id': item_id},
                    success=False,
                    error='No se pudo obtener token de acceso válido'
                )
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido'
                }
            
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Endpoint para obtener información del item
            url = f"{EPIC_CATALOG_API}/namespace/fn/items/{item_id}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    item_data = await response.json()
                    processed_item = self._process_item(item_data)
                    
                    # Registrar acción exitosa
                    self.action_logger.log_action(
                        'item_info',
                        user_id,
                        {'item_id': item_id},
                        success=True
                    )
                    
                    # Delay natural post-acción
                    await self.rate_limiter.apply_natural_delay('item_info')
                    
                    return {
                        'success': True,
                        'item': processed_item
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error obteniendo item: {response.status} - {error_text}")
                    return {
                        'success': False,
                        'error': f'Item no encontrado: {item_id}'
                    }
                    
        except Exception as e:
            log.error(f"Error en get_item_info: {e}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    async def close(self):
        """Cierra las conexiones"""
        await self.auth.close()

