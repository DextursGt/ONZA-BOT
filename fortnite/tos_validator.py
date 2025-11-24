"""
Validador de TOS de Epic Games
Asegura que todas las acciones cumplan con los términos de servicio
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

log = logging.getLogger('fortnite-tos-validator')


class TOSValidator:
    """
    Valida que las acciones cumplan con los TOS de Epic Games
    """
    
    # Acciones permitidas según TOS
    ALLOWED_ACTIONS = {
        'friend_add': True,      # Permitido: agregar amigos
        'friend_list': True,     # Permitido: listar amigos
        'gift_send': True,      # Permitido: enviar regalos (con límites)
        'store_get': True,      # Permitido: consultar tienda
        'item_info': True,      # Permitido: consultar info de items
        'account_switch': True, # Permitido: cambiar cuenta activa
        'token_refresh': True   # Permitido: refrescar tokens
    }
    
    # Límites de TOS (más restrictivos que rate limits técnicos)
    TOS_LIMITS = {
        'gift_send_per_day': 10,        # Máximo 10 regalos por día por cuenta
        'friend_add_per_day': 20,        # Máximo 20 amigos por día
        'api_calls_per_hour': 1000       # Máximo 1000 llamadas API por hora
    }
    
    def __init__(self):
        """Inicializa el validador TOS"""
        self.daily_counts: Dict[str, Dict[str, int]] = {}  # {account_id: {action: count}}
        self.hourly_api_calls: Dict[str, List[datetime]] = {}  # {account_id: [timestamps]}
        
        log.info("TOS Validator inicializado")
    
    def validate_action(
        self,
        action_type: str,
        account_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Valida si una acción está permitida según TOS
        
        Args:
            action_type: Tipo de acción
            account_id: ID de la cuenta
            details: Detalles adicionales de la acción
            
        Returns:
            Tupla (permitido, mensaje_error)
        """
        # 1. Verificar si la acción está en la lista permitida
        if action_type not in self.ALLOWED_ACTIONS:
            return False, f"Acción '{action_type}' no está permitida según TOS"
        
        if not self.ALLOWED_ACTIONS[action_type]:
            return False, f"Acción '{action_type}' está deshabilitada"
        
        # 2. Verificar límites diarios por cuenta
        today = datetime.utcnow().date().isoformat()
        account_key = f"{account_id}_{today}"
        
        if account_key not in self.daily_counts:
            self.daily_counts[account_key] = {}
        
        counts = self.daily_counts[account_key]
        
        # Verificar límite de regalos por día
        if action_type == 'gift_send':
            gift_count = counts.get('gift_send', 0)
            if gift_count >= self.TOS_LIMITS['gift_send_per_day']:
                return False, (
                    f"Límite diario de regalos alcanzado ({self.TOS_LIMITS['gift_send_per_day']}). "
                    "Espera hasta mañana o usa otra cuenta."
                )
        
        # Verificar límite de agregar amigos por día
        if action_type == 'friend_add':
            friend_count = counts.get('friend_add', 0)
            if friend_count >= self.TOS_LIMITS['friend_add_per_day']:
                return False, (
                    f"Límite diario de agregar amigos alcanzado ({self.TOS_LIMITS['friend_add_per_day']}). "
                    "Espera hasta mañana."
                )
        
        # 3. Verificar límite de llamadas API por hora
        if account_id not in self.hourly_api_calls:
            self.hourly_api_calls[account_id] = []
        
        # Limpiar llamadas antiguas (más de 1 hora)
        cutoff = datetime.utcnow().timestamp() - 3600
        self.hourly_api_calls[account_id] = [
            ts for ts in self.hourly_api_calls[account_id]
            if ts.timestamp() > cutoff
        ]
        
        if len(self.hourly_api_calls[account_id]) >= self.TOS_LIMITS['api_calls_per_hour']:
            return False, (
                f"Límite de llamadas API por hora alcanzado ({self.TOS_LIMITS['api_calls_per_hour']}). "
                "Espera antes de continuar."
            )
        
        # 4. Validaciones específicas por tipo de acción
        if action_type == 'gift_send' and details:
            # Validar que el item_id es válido
            item_id = details.get('item_id')
            if not item_id or not isinstance(item_id, str):
                return False, "Item ID inválido para regalo"
            
            # Validar que el destinatario es válido
            recipient = details.get('recipient')
            if not recipient or not isinstance(recipient, str):
                return False, "Destinatario inválido para regalo"
        
        if action_type == 'friend_add' and details:
            # Validar que el username es válido
            username = details.get('username')
            if not username or not isinstance(username, str) or len(username) < 3:
                return False, "Username inválido para agregar como amigo"
        
        # Acción permitida
        return True, None
    
    def record_action(
        self,
        action_type: str,
        account_id: str
    ) -> None:
        """
        Registra una acción para conteo de límites TOS
        
        Args:
            action_type: Tipo de acción
            account_id: ID de la cuenta
        """
        today = datetime.utcnow().date().isoformat()
        account_key = f"{account_id}_{today}"
        
        if account_key not in self.daily_counts:
            self.daily_counts[account_key] = {}
        
        # Incrementar contador
        if action_type not in self.daily_counts[account_key]:
            self.daily_counts[account_key][action_type] = 0
        
        self.daily_counts[account_key][action_type] += 1
        
        # Registrar llamada API
        if account_id not in self.hourly_api_calls:
            self.hourly_api_calls[account_id] = []
        
        self.hourly_api_calls[account_id].append(datetime.utcnow())
        
        log.debug(f"Acción {action_type} registrada para cuenta {account_id}")
    
    def get_daily_count(
        self,
        action_type: str,
        account_id: str
    ) -> int:
        """
        Obtiene el conteo diario de una acción
        
        Args:
            action_type: Tipo de acción
            account_id: ID de la cuenta
            
        Returns:
            Número de acciones hoy
        """
        today = datetime.utcnow().date().isoformat()
        account_key = f"{account_id}_{today}"
        
        if account_key not in self.daily_counts:
            return 0
        
        return self.daily_counts[account_key].get(action_type, 0)
    
    def get_remaining_quota(
        self,
        action_type: str,
        account_id: str
    ) -> int:
        """
        Obtiene la cuota restante para una acción
        
        Args:
            action_type: Tipo de acción
            account_id: ID de la cuenta
            
        Returns:
            Cuota restante
        """
        if action_type == 'gift_send':
            used = self.get_daily_count(action_type, account_id)
            return max(0, self.TOS_LIMITS['gift_send_per_day'] - used)
        elif action_type == 'friend_add':
            used = self.get_daily_count(action_type, account_id)
            return max(0, self.TOS_LIMITS['friend_add_per_day'] - used)
        
        return -1  # Sin límite específico


# Instancia global del validador TOS
_tos_validator = TOSValidator()


def get_tos_validator() -> TOSValidator:
    """Obtiene la instancia global del validador TOS"""
    return _tos_validator

