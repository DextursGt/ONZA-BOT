"""
Módulo de Rate Limiting y Delays Naturales
Previene baneos por exceso de requests a la API de Epic Games
"""

import asyncio
import time
import random
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger('fortnite-rate-limiter')


class RateLimiter:
    """
    Rate limiter con delays naturales para prevenir baneos
    """
    
    def __init__(self):
        """Inicializa el rate limiter"""
        # Límites por tipo de acción (requests por minuto)
        self.limits = {
            'friend_add': 5,      # Máximo 5 agregar amigos por minuto
            'friend_list': 10,    # Máximo 10 listar amigos por minuto
            'gift_send': 3,       # Máximo 3 regalos por minuto (muy restrictivo)
            'store_get': 20,      # Máximo 20 consultas de tienda por minuto
            'item_info': 30,      # Máximo 30 consultas de items por minuto
            'token_refresh': 10,  # Máximo 10 refrescos de token por minuto
            'account_switch': 5   # Máximo 5 cambios de cuenta por minuto
        }
        
        # Delays naturales entre acciones (en segundos)
        self.natural_delays = {
            'friend_add': (2.0, 5.0),      # Entre 2-5 segundos
            'friend_list': (1.0, 3.0),      # Entre 1-3 segundos
            'gift_send': (5.0, 10.0),       # Entre 5-10 segundos (muy conservador)
            'store_get': (1.0, 2.0),        # Entre 1-2 segundos
            'item_info': (0.5, 1.5),        # Entre 0.5-1.5 segundos
            'token_refresh': (2.0, 4.0),    # Entre 2-4 segundos
            'account_switch': (1.0, 2.0)     # Entre 1-2 segundos
        }
        
        # Registro de acciones por tipo
        self.action_history: Dict[str, List[float]] = defaultdict(list)
        
        # Última acción por tipo (para delays naturales)
        self.last_action_time: Dict[str, float] = {}
        
        # Cooldown global (evitar acciones muy rápidas)
        self.global_cooldown = 0.5  # Mínimo 0.5 segundos entre cualquier acción
        
        log.info("Rate limiter inicializado")
    
    async def wait_if_needed(self, action_type: str) -> None:
        """
        Espera si es necesario según rate limits y delays naturales
        
        Args:
            action_type: Tipo de acción a realizar
        """
        current_time = time.time()
        
        # 1. Verificar delay natural desde última acción del mismo tipo
        if action_type in self.last_action_time:
            last_time = self.last_action_time[action_type]
            if action_type in self.natural_delays:
                min_delay, max_delay = self.natural_delays[action_type]
                elapsed = current_time - last_time
                
                if elapsed < min_delay:
                    # Esperar el tiempo restante + un poco aleatorio
                    wait_time = min_delay - elapsed + random.uniform(0, 0.5)
                    log.debug(f"Delay natural para {action_type}: {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
        
        # 2. Verificar rate limit
        if action_type in self.limits:
            # Limpiar acciones antiguas (más de 1 minuto)
            cutoff_time = current_time - 60
            self.action_history[action_type] = [
                t for t in self.action_history[action_type] if t > cutoff_time
            ]
            
            # Verificar si se excedió el límite
            if len(self.action_history[action_type]) >= self.limits[action_type]:
                # Calcular tiempo de espera hasta que expire la acción más antigua
                oldest_action = min(self.action_history[action_type])
                wait_time = (oldest_action + 60) - current_time + 0.1
                
                if wait_time > 0:
                    log.warning(
                        f"Rate limit alcanzado para {action_type}. "
                        f"Esperando {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
        
        # 3. Cooldown global (evitar acciones muy rápidas)
        if hasattr(self, '_last_global_action'):
            elapsed = current_time - self._last_global_action
            if elapsed < self.global_cooldown:
                wait_time = self.global_cooldown - elapsed
                await asyncio.sleep(wait_time)
                current_time = time.time()
        
        # Registrar acción
        self.action_history[action_type].append(current_time)
        self.last_action_time[action_type] = current_time
        self._last_global_action = current_time
    
    async def apply_natural_delay(self, action_type: str) -> None:
        """
        Aplica un delay natural después de una acción
        
        Args:
            action_type: Tipo de acción realizada
        """
        if action_type in self.natural_delays:
            min_delay, max_delay = self.natural_delays[action_type]
            delay = random.uniform(min_delay, max_delay)
            
            # Añadir variación humana (a veces más rápido, a veces más lento)
            human_variation = random.choice([0.8, 1.0, 1.2, 1.5])
            final_delay = delay * human_variation
            
            log.debug(f"Delay natural post-acción para {action_type}: {final_delay:.2f}s")
            await asyncio.sleep(final_delay)
    
    def get_stats(self) -> Dict[str, any]:
        """
        Obtiene estadísticas del rate limiter
        
        Returns:
            Diccionario con estadísticas
        """
        current_time = time.time()
        stats = {}
        
        for action_type, history in self.action_history.items():
            # Limpiar acciones antiguas
            cutoff_time = current_time - 60
            recent_actions = [t for t in history if t > cutoff_time]
            self.action_history[action_type] = recent_actions
            
            limit = self.limits.get(action_type, 0)
            stats[action_type] = {
                'actions_last_minute': len(recent_actions),
                'limit': limit,
                'percentage_used': (len(recent_actions) / limit * 100) if limit > 0 else 0
            }
        
        return stats


class ActionLogger:
    """
    Registra todas las acciones para auditoría y prevención de baneos
    """
    
    def __init__(self):
        """Inicializa el logger de acciones"""
        self.actions: List[Dict] = []
        self.max_actions = 1000  # Mantener últimas 1000 acciones
        
        log.info("Action logger inicializado")
    
    def log_action(
        self,
        action_type: str,
        user_id: int,
        details: Dict,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Registra una acción
        
        Args:
            action_type: Tipo de acción
            user_id: ID del usuario que ejecutó la acción
            details: Detalles de la acción
            success: Si la acción fue exitosa
            error: Mensaje de error si falló
        """
        action_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action_type,
            'user_id': user_id,
            'details': details,
            'success': success,
            'error': error
        }
        
        self.actions.append(action_record)
        
        # Mantener solo las últimas acciones
        if len(self.actions) > self.max_actions:
            self.actions = self.actions[-self.max_actions:]
        
        # Log según resultado
        if success:
            log.info(f"Acción registrada: {action_type} por usuario {user_id}")
        else:
            log.warning(f"Acción fallida registrada: {action_type} por usuario {user_id} - {error}")
    
    def get_recent_actions(
        self,
        action_type: Optional[str] = None,
        minutes: int = 60
    ) -> List[Dict]:
        """
        Obtiene acciones recientes
        
        Args:
            action_type: Filtrar por tipo (opcional)
            minutes: Últimos N minutos
            
        Returns:
            Lista de acciones
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        filtered = [
            action for action in self.actions
            if datetime.fromisoformat(action['timestamp']) > cutoff_time
        ]
        
        if action_type:
            filtered = [a for a in filtered if a['action_type'] == action_type]
        
        return filtered
    
    def get_action_count(
        self,
        action_type: str,
        minutes: int = 60
    ) -> int:
        """
        Cuenta acciones de un tipo en los últimos N minutos
        
        Args:
            action_type: Tipo de acción
            minutes: Últimos N minutos
            
        Returns:
            Número de acciones
        """
        return len(self.get_recent_actions(action_type, minutes))


# Instancia global del rate limiter
_rate_limiter = RateLimiter()
_action_logger = ActionLogger()


def get_rate_limiter() -> RateLimiter:
    """Obtiene la instancia global del rate limiter"""
    return _rate_limiter


def get_action_logger() -> ActionLogger:
    """Obtiene la instancia global del action logger"""
    return _action_logger

