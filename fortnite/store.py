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

# Base URL de la API de Epic Games para la tienda (puede no estar disponible)
EPIC_CATALOG_API = "https://catalog-public-service-prod.ol.epicgames.com/catalog/api/shared"

# API pública alternativa (fortnite-api.com)
FORTNITE_API_PUBLIC = "https://fortnite-api.com/v2"
FORTNITE_API_KEY = "252af500-bfeb-45d3-b90f-c25ef082a1f1"  # API key de fortnite-api.com


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
            log.info("[DEBUG] [STORE] _get_valid_access_token called")
            account = self.account_manager.get_account()
            if not account:
                log.error("[DEBUG] [STORE] No hay cuenta activa")
                log.error("No hay cuenta activa - usa !fn_switch para activar una cuenta o !fn_login para agregar una")
                return None
            
            log.info(f"[DEBUG] [STORE] Account found - Account #: {account.get('account_number')}, Account ID: {account.get('account_id', 'None')}")
            
            # Obtener refresh_token (único token almacenado)
            encrypted_refresh_token = account.get('encrypted_refresh_token')
            if not encrypted_refresh_token:
                log.error(f"[DEBUG] [STORE] No encrypted_refresh_token found")
                log.error(f"No hay refresh_token disponible para cuenta {account.get('account_name', 'desconocida')} - necesitas autenticarte con !fn_login")
                return None
            
            log.info(f"[DEBUG] [STORE] Found encrypted_refresh_token (length: {len(encrypted_refresh_token)})")
            
            # Usar OAuth para refrescar y obtener access_token
            from .oauth import EpicOAuth
            oauth = EpicOAuth()
            
            log.info("[DEBUG] [STORE] Calling refresh_access_token...")
            new_tokens = await oauth.refresh_access_token(encrypted_refresh_token)
            
            if new_tokens and new_tokens.get('access_token'):
                access_masked = f"{new_tokens['access_token'][:10]}...{new_tokens['access_token'][-5:]}" if new_tokens.get('access_token') else 'None'
                log.info(f"[DEBUG] [STORE] Access token obtained: {access_masked}")
                
                # Actualizar refresh_token si viene uno nuevo
                if new_tokens.get('refresh_token'):
                    log.info("[DEBUG] [STORE] New refresh_token received, updating...")
                    encrypted_new_refresh = self.auth.encrypt_token(new_tokens['refresh_token'])
                    update_success = self.account_manager.update_account_token(
                        account.get('account_number'),
                        encrypted_new_refresh,
                        new_tokens.get('expires_at')
                    )
                    log.info(f"[DEBUG] [STORE] Refresh token updated: {update_success}")
                
                log.info("Access_token obtenido correctamente")
                return new_tokens['access_token']
            else:
                log.error("[DEBUG] [STORE] refresh_access_token returned None or no access_token")
                log.error("Error refrescando token - el refresh_token puede estar expirado o ser inválido. Usa !fn_login para reautenticarte")
                return None
            
        except Exception as e:
            log.error(f"[DEBUG] [STORE] Exception in _get_valid_access_token: {e}")
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
            
            # 3. Intentar primero con API pública (más confiable)
            log.info("Intentando obtener tienda desde API pública...")
            result = await self._get_store_fallback()
            
            if result.get('success'):
                return result
            
            # 4. Si falla, intentar con API oficial (puede no estar disponible)
            log.info("API pública falló, intentando con API oficial de Epic Games...")
            access_token = await self._get_valid_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'No se pudo obtener token de acceso válido. La API oficial puede no estar disponible.',
                    'items': []
                }
            
            session = await self.auth._get_session()
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            # Endpoint para obtener la tienda (puede no estar disponible)
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
                    
                    log.info(f"Tienda obtenida desde API oficial: {len(items)} items")
                    return {
                        'success': True,
                        'items': items,
                        'cached': False,
                        'count': len(items),
                        'source': 'epic_official'
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error obteniendo tienda desde API oficial: {response.status} - {error_text}")
                    
                    return {
                        'success': False,
                        'error': f'Las APIs de Epic Games no están disponibles (Error {response.status}). Intenta más tarde.',
                        'items': []
                    }
                    
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
            # Usar API pública de Fortnite (fortnite-api.com) con API key
            session = await self.auth._get_session()
            url = f"{FORTNITE_API_PUBLIC}/shop"
            
            headers = {
                'Authorization': FORTNITE_API_KEY,
                'Content-Type': 'application/json'
            }
            
            log.info(f"Consultando API pública: {url}")
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Log para debugging
                    log.info(f"Respuesta de API: status={data.get('status')}, keys={list(data.keys())}")
                    
                    # Verificar estructura de respuesta de fortnite-api.com
                    # La respuesta tiene: {"status": 200, "data": {...}}
                    if data.get('status') == 200 and 'data' in data:
                        # Log estructura de data
                        data_keys = list(data['data'].keys()) if isinstance(data.get('data'), dict) else []
                        log.info(f"Estructura de data: {data_keys}")
                        
                        items = await self._process_fortnite_api_items(data)
                        
                        log.info(f"Items procesados: {len(items)}")
                        
                        if items:
                            self.cache = {'items': items}
                            self.cache_time = datetime.utcnow()
                            
                            log.info(f"Tienda obtenida desde API pública: {len(items)} items")
                            return {
                                'success': True,
                                'items': items,
                                'cached': False,
                                'count': len(items),
                                'source': 'fortnite-api.com'
                            }
                        else:
                            log.warning("No se pudieron procesar items de la respuesta")
                            # Log una muestra de la estructura para debugging
                            if isinstance(data.get('data'), dict):
                                log.warning(f"Muestra de data: {str(data['data'])[:500]}")
                            return {
                                'success': False,
                                'error': 'No se pudieron procesar los items de la tienda',
                                'items': []
                            }
                    else:
                        log.warning(f"Estructura de respuesta inesperada: status={data.get('status')}, keys={list(data.keys())}")
                        # Log respuesta completa para debugging
                        log.warning(f"Respuesta completa: {str(data)[:1000]}")
                        return {
                            'success': False,
                            'error': 'La API pública devolvió datos en formato inesperado',
                            'items': []
                        }
                elif response.status == 404:
                    log.error("API pública no encontrada (404)")
                    return {
                        'success': False,
                        'error': 'La API pública de Fortnite no está disponible (404)',
                        'items': []
                    }
                else:
                    error_text = await response.text()
                    log.error(f"Error en API pública: {response.status} - {error_text[:200]}")
                    return {
                        'success': False,
                        'error': f'Error en API pública: {response.status}',
                        'items': []
                    }
        except Exception as e:
            log.error(f"Error en fallback: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
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
    
    async def _process_fortnite_api_items(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Procesa items de la API pública de Fortnite (fortnite-api.com)
        
        Args:
            api_data: Datos de la API pública con estructura {"status": 200, "data": {...}}
            
        Returns:
            Lista de items procesados
        """
        items = []
        
        try:
            # Estructura de fortnite-api.com: {"status": 200, "data": {...}}
            data = api_data.get('data', {})
            
            log.info(f"Procesando data, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            
            # La tienda puede tener diferentes estructuras:
            # Opción 1: "featured" y "daily" como objetos con "entries"
            # Opción 2: "featured" y "daily" como arrays directamente
            # Opción 3: Estructura diferente
            
            featured_entries = []
            daily_entries = []
            
            # Intentar diferentes estructuras
            if 'featured' in data:
                featured = data['featured']
                if isinstance(featured, dict) and 'entries' in featured:
                    featured_entries = featured['entries']
                elif isinstance(featured, list):
                    featured_entries = featured
            
            if 'daily' in data:
                daily = data['daily']
                if isinstance(daily, dict) and 'entries' in daily:
                    daily_entries = daily['entries']
                elif isinstance(daily, list):
                    daily_entries = daily
            
            # También intentar buscar directamente "entries" en el nivel superior
            if not featured_entries and not daily_entries and 'entries' in data:
                all_entries = data['entries'] if isinstance(data.get('entries'), list) else []
                # Intentar separar por sección si existe
                for entry in all_entries:
                    section = entry.get('section', {})
                    if isinstance(section, dict) and section.get('id') == 'featured':
                        featured_entries.append(entry)
                    else:
                        daily_entries.append(entry)
            
            log.info(f"Featured entries: {len(featured_entries)}, Daily entries: {len(daily_entries)}")
            
            all_entries = featured_entries + daily_entries
            
            # Primero, obtener todos los item_ids que necesitan nombres
            items_needing_names = []
            
            for idx, entry in enumerate(all_entries):
                try:
                    # Log primera entry para debugging
                    if idx == 0:
                        log.info(f"Ejemplo de entry keys: {list(entry.keys())}")
                        log.info(f"Ejemplo de entry (primeros 500 chars): {str(entry)[:500]}")
                    
                    # Obtener información del bundle o del primer item
                    bundle = entry.get('bundle', {})
                    items_list = entry.get('items', [])
                    first_item = items_list[0] if items_list else {}
                    
                    # Obtener item_id y first_item_id primero
                    item_id = entry.get('offerId', entry.get('id', ''))
                    first_item_id = ''
                    if first_item and isinstance(first_item, dict):
                        first_item_id = first_item.get('id', '') or first_item.get('itemId', '') or first_item.get('itemId', '')
                    
                    # Obtener nombre - buscar en múltiples lugares
                    name = ''
                    
                    # 1. Buscar en el entry directamente
                    name = (entry.get('name', '') or 
                           entry.get('title', '') or 
                           entry.get('displayName', '') or
                           entry.get('bundleName', ''))
                    
                    # 2. Buscar en bundle
                    if not name and bundle:
                        if isinstance(bundle, dict):
                            name = (bundle.get('name', '') or 
                                   bundle.get('title', '') or 
                                   bundle.get('displayName', '') or
                                   bundle.get('bundleName', ''))
                    
                    # 3. Buscar en el primer item
                    if not name and first_item:
                        if isinstance(first_item, dict):
                            name = (first_item.get('name', '') or 
                                   first_item.get('title', '') or 
                                   first_item.get('displayName', '') or
                                   first_item.get('itemName', ''))
                    
                    # 4. Si aún no hay nombre y tenemos first_item_id, intentar obtenerlo de la API de cosméticos
                    # Nota: Esto se hará después de procesar todos los items para evitar muchas llamadas API
                    # Por ahora, guardamos el first_item_id para obtener el nombre después si es necesario
                    
                    # 5. Si aún no hay nombre, usar el item_id como fallback
                    if not name:
                        if first_item_id:
                            # Limpiar el ID para que sea más legible
                            name = first_item_id.replace('Athena', '').replace('Character', '').replace('_', ' ')
                        elif item_id:
                            name = item_id
                        else:
                            name = 'Unknown'
                    
                    # Obtener precio - buscar en múltiples lugares
                    final_price = 0
                    regular_price = 0
                    
                    # 1. Buscar en pricing
                    pricing = entry.get('pricing', {})
                    if isinstance(pricing, dict):
                        final_price = pricing.get('finalPrice', pricing.get('finalPrice', pricing.get('price', 0)))
                        regular_price = pricing.get('regularPrice', pricing.get('regularPrice', final_price))
                    
                    # 2. Buscar directamente en entry
                    if not final_price:
                        final_price = entry.get('finalPrice', entry.get('price', entry.get('finalPrice', 0)))
                        regular_price = entry.get('regularPrice', entry.get('regularPrice', final_price))
                    
                    # 3. Buscar en bundle
                    if not final_price and bundle and isinstance(bundle, dict):
                        bundle_pricing = bundle.get('pricing', {})
                        if isinstance(bundle_pricing, dict):
                            final_price = bundle_pricing.get('finalPrice', bundle_pricing.get('price', 0))
                            regular_price = bundle_pricing.get('regularPrice', final_price)
                        else:
                            final_price = bundle.get('finalPrice', bundle.get('price', 0))
                            regular_price = bundle.get('regularPrice', final_price)
                    
                    # Si aún no hay precio, intentar obtenerlo de los items
                    if not final_price and items_list:
                        for item in items_list:
                            if isinstance(item, dict):
                                item_pricing = item.get('pricing', {})
                                if isinstance(item_pricing, dict):
                                    item_price = item_pricing.get('finalPrice', item_pricing.get('price', 0))
                                    if item_price:
                                        final_price = item_price
                                        break
                    
                    # Obtener rareza
                    rarity = 'common'
                    if first_item:
                        item_rarity = first_item.get('rarity', {})
                        if isinstance(item_rarity, dict):
                            rarity = item_rarity.get('value', item_rarity.get('displayValue', 'common'))
                        elif isinstance(item_rarity, str):
                            rarity = item_rarity
                    
                    # Obtener tipo
                    item_type = 'unknown'
                    if first_item:
                        item_type_obj = first_item.get('type', {})
                        if isinstance(item_type_obj, dict):
                            item_type = item_type_obj.get('value', item_type_obj.get('displayValue', 'unknown'))
                        elif isinstance(item_type_obj, str):
                            item_type = item_type_obj
                    
                    # Obtener imagen - buscar en múltiples lugares
                    image_url = ''
                    
                    # 1. Buscar en newDisplayAsset o displayAsset
                    display_asset = entry.get('newDisplayAsset', {}) or entry.get('displayAsset', {})
                    if display_asset and isinstance(display_asset, dict):
                        # Intentar diferentes estructuras
                        material_instances = display_asset.get('materialInstances', [])
                        if material_instances and isinstance(material_instances, list) and len(material_instances) > 0:
                            images = material_instances[0].get('images', {})
                            if isinstance(images, dict):
                                image_url = (images.get('Background', '') or 
                                           images.get('OfferImage', '') or 
                                           images.get('icon', '') or
                                           images.get('smallIcon', ''))
                        
                        # También buscar directamente en displayAsset
                        if not image_url:
                            image_url = display_asset.get('image', '') or display_asset.get('url', '')
                    
                    # 2. Buscar en bundle
                    if not image_url and bundle and isinstance(bundle, dict):
                        bundle_images = bundle.get('images', {})
                        if isinstance(bundle_images, dict):
                            image_url = (bundle_images.get('icon', '') or 
                                       bundle_images.get('smallIcon', '') or
                                       bundle_images.get('featured', '') or
                                       bundle_images.get('background', ''))
                    
                    # 3. Buscar en el primer item
                    if not image_url and first_item and isinstance(first_item, dict):
                        item_images = first_item.get('images', {})
                        if isinstance(item_images, dict):
                            image_url = (item_images.get('icon', '') or 
                                       item_images.get('smallIcon', '') or
                                       item_images.get('featured', '') or
                                       item_images.get('background', ''))
                    
                    # 4. Si hay item_id, construir URL de imagen de fortnite-api.com
                    if not image_url and first_item_id:
                        # Formato: https://fortnite-api.com/images/cosmetics/br/{item_id}/icon.png
                        image_url = f"https://fortnite-api.com/images/cosmetics/br/{first_item_id}/icon.png"
                    
                    # Para regalos, necesitamos el ID del item real, no el offerId
                    # Si hay first_item_id, usarlo; si no, usar item_id como fallback
                    gift_item_id = first_item_id if first_item_id else item_id
                    
                    # Si no hay nombre, guardar para obtenerlo después
                    if not name or name == 'Unknown':
                        items_needing_names.append({
                            'item_id': gift_item_id,
                            'first_item_id': first_item_id,
                            'entry': entry
                        })
                    
                    item_data = {
                        'item_id': gift_item_id,  # ID para usar en !fn_gift
                        'offer_id': item_id,  # ID de la oferta (para referencia)
                        'name': name if name and name != 'Unknown' else (first_item_id if first_item_id else item_id),
                        'price': final_price,
                        'original_price': regular_price,
                        'rarity': rarity,
                        'type': item_type,
                        'image_url': image_url,
                        'is_featured': entry.get('section', {}).get('id') == 'featured' if isinstance(entry.get('section'), dict) else False,
                        'needs_name_lookup': not name or name == 'Unknown'
                    }
                    items.append(item_data)
                except Exception as e:
                    log.error(f"Error procesando entry individual (índice {idx}): {e}")
                    import traceback
                    log.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            # Obtener nombres faltantes desde la API de cosméticos (solo los primeros 20 para no hacer demasiadas llamadas)
            if items_needing_names:
                log.info(f"Obteniendo nombres para {min(len(items_needing_names), 20)} items desde API de cosméticos...")
                session_cosmetics = await self.auth._get_session()
                headers_cosmetics = {
                    'Authorization': FORTNITE_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                for item_info in items_needing_names[:20]:  # Limitar a 20 para no hacer demasiadas llamadas
                    try:
                        item_id_to_lookup = item_info.get('first_item_id') or item_info.get('item_id')
                        if not item_id_to_lookup:
                            continue
                        
                        async with session_cosmetics.get(
                            f"{FORTNITE_API_PUBLIC}/cosmetics/br/{item_id_to_lookup}",
                            headers=headers_cosmetics
                        ) as cosmetic_response:
                            if cosmetic_response.status == 200:
                                cosmetic_data = await cosmetic_response.json()
                                if cosmetic_data.get('status') == 200 and 'data' in cosmetic_data:
                                    cosmetic_name = cosmetic_data['data'].get('name', '')
                                    if cosmetic_name:
                                        # Actualizar el nombre en el item correspondiente
                                        target_item_id = item_info.get('item_id')
                                        for item in items:
                                            if item.get('item_id') == target_item_id:
                                                item['name'] = cosmetic_name
                                                log.info(f"Nombre actualizado: {cosmetic_name} para {item_id_to_lookup}")
                                                break
                    except Exception as e:
                        log.debug(f"Error obteniendo nombre para {item_info.get('item_id')}: {e}")
                        continue
                
        except Exception as e:
            log.error(f"Error procesando items de API pública: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
        
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
        Obtiene información detallada de un item específico usando fortnite-api.com
        
        Args:
            item_id: ID del item
            
        Returns:
            Diccionario con información del item o error
        """
        try:
            # 1. Rate limiting y delay natural
            await self.rate_limiter.wait_if_needed('item_info')
            
            # 2. Intentar primero con API pública de fortnite-api.com
            session = await self.auth._get_session()
            headers = {
                'Authorization': FORTNITE_API_KEY,
                'Content-Type': 'application/json'
            }
            
            # Buscar el item en la API de cosméticos
            url = f"{FORTNITE_API_PUBLIC}/cosmetics/br/{item_id}"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 200 and 'data' in data:
                        item_data = data['data']
                        
                        # Procesar información del item
                        processed_item = {
                            'item_id': item_data.get('id', item_id),
                            'name': item_data.get('name', 'Unknown'),
                            'description': item_data.get('description', ''),
                            'rarity': item_data.get('rarity', {}).get('value', 'common') if isinstance(item_data.get('rarity'), dict) else item_data.get('rarity', 'common'),
                            'type': item_data.get('type', {}).get('value', 'unknown') if isinstance(item_data.get('type'), dict) else item_data.get('type', 'unknown'),
                            'image_url': item_data.get('images', {}).get('icon', '') or item_data.get('images', {}).get('smallIcon', ''),
                            'set': item_data.get('set', {}).get('value', '') if item_data.get('set') else '',
                            'series': item_data.get('series', {}).get('value', '') if item_data.get('series') else '',
                            'introduction': item_data.get('introduction', {}).get('text', '') if item_data.get('introduction') else '',
                            'source': 'fortnite-api.com'
                        }
                        
                        self.action_logger.log_action(
                            'item_info',
                            user_id,
                            {'item_id': item_id},
                            success=True
                        )
                        
                        return {
                            'success': True,
                            'item': processed_item
                        }
            
            # Si falla la API pública, intentar con API oficial (puede no estar disponible)
            access_token = await self._get_valid_access_token()
            if access_token:
                headers_official = {
                    'Authorization': f'Bearer {access_token}'
                }
                
                url_official = f"{EPIC_CATALOG_API}/namespace/fn/items/{item_id}"
                
                async with session.get(url_official, headers=headers_official) as response:
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
                        log.error(f"Error obteniendo item desde API oficial: {response.status} - {error_text}")
            
            # Si ambas APIs fallan
            self.action_logger.log_action(
                'item_info',
                user_id,
                {'item_id': item_id},
                success=False,
                error='Item no encontrado en ninguna API'
            )
            return {
                'success': False,
                'error': f'Item no encontrado: {item_id}'
            }
                    
        except Exception as e:
            log.error(f"Error en get_item_info: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    async def close(self):
        """Cierra las conexiones"""
        await self.auth.close()

