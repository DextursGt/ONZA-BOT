"""
Módulo de gestión de cuentas de Fortnite
Permite gestionar hasta 5 cuentas del owner
"""

import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
from data_manager import load_data, save_data
import logging

log = logging.getLogger('fortnite-accounts')

# Límite máximo de cuentas
MAX_ACCOUNTS = 5
DATA_KEY = 'fortnite_accounts'


class FortniteAccountManager:
    """Gestiona las cuentas de Fortnite del owner"""
    
    def __init__(self):
        """Inicializa el gestor de cuentas"""
        self.owner_id = 857134594028601364
    
    def _get_accounts_data(self) -> Dict[str, Any]:
        """
        Obtiene los datos de cuentas desde el almacenamiento
        
        Returns:
            Diccionario con datos de cuentas
        """
        data = load_data()
        if DATA_KEY not in data:
            data[DATA_KEY] = {}
        return data[DATA_KEY]
    
    def _save_accounts_data(self, accounts: Dict[str, Any]):
        """
        Guarda los datos de cuentas
        
        Args:
            accounts: Diccionario con datos de cuentas
        """
        data = load_data()
        data[DATA_KEY] = accounts
        save_data(data)
    
    def add_account(
        self, 
        account_number: int,
        account_name: str,
        encrypted_access_token: str,
        encrypted_refresh_token: str,
        account_id: str,
        expires_at: str,
        device_id: Optional[str] = None
    ) -> bool:
        """
        Agrega una nueva cuenta de Fortnite
        
        Args:
            account_number: Número de cuenta (1-5)
            account_name: Nombre descriptivo de la cuenta
            encrypted_access_token: Token de acceso cifrado
            encrypted_refresh_token: Token de refresco cifrado
            account_id: ID de la cuenta de Epic
            expires_at: Fecha de expiración del token
            device_id: ID del dispositivo (opcional)
            
        Returns:
            True si se agregó correctamente, False en caso contrario
        """
        if account_number < 1 or account_number > MAX_ACCOUNTS:
            log.error(f"Número de cuenta inválido: {account_number}")
            return False
        
        accounts = self._get_accounts_data()
        
        # Verificar si ya existe una cuenta con ese número
        for acc_id, acc_data in accounts.items():
            if acc_data.get('account_number') == account_number:
                log.warning(f"Cuenta número {account_number} ya existe, actualizando...")
                # Actualizar cuenta existente
                accounts[acc_id].update({
                    'account_name': account_name,
                    'encrypted_access_token': encrypted_access_token,
                    'encrypted_refresh_token': encrypted_refresh_token,
                    'account_id': account_id,
                    'expires_at': expires_at,
                    'device_id': device_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
                self._save_accounts_data(accounts)
                return True
        
        # Verificar límite de cuentas
        if len(accounts) >= MAX_ACCOUNTS:
            log.error(f"Límite de {MAX_ACCOUNTS} cuentas alcanzado")
            return False
        
        # Crear nueva cuenta
        account_data = {
            'account_number': account_number,
            'account_name': account_name,
            'encrypted_access_token': encrypted_access_token,
            'encrypted_refresh_token': encrypted_refresh_token,
            'account_id': account_id,
            'expires_at': expires_at,
            'device_id': device_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        accounts[account_id] = account_data
        self._save_accounts_data(accounts)
        log.info(f"Cuenta {account_number} ({account_name}) agregada correctamente")
        return True
    
    def get_account(self, account_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene una cuenta específica o la cuenta activa
        
        Args:
            account_number: Número de cuenta (1-5) o None para cuenta activa
            
        Returns:
            Datos de la cuenta o None si no existe
        """
        accounts = self._get_accounts_data()
        
        if account_number is None:
            # Buscar cuenta activa
            for acc_data in accounts.values():
                if acc_data.get('is_active', False):
                    return acc_data
            return None
        
        # Buscar por número
        for acc_data in accounts.values():
            if acc_data.get('account_number') == account_number:
                return acc_data
        
        return None
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        Lista todas las cuentas registradas
        
        Returns:
            Lista de diccionarios con información de cuentas (sin tokens)
        """
        accounts = self._get_accounts_data()
        result = []
        
        for acc_id, acc_data in accounts.items():
            result.append({
                'account_number': acc_data.get('account_number'),
                'account_name': acc_data.get('account_name'),
                'account_id': acc_data.get('account_id'),
                'is_active': acc_data.get('is_active', False),
                'created_at': acc_data.get('created_at'),
                'updated_at': acc_data.get('updated_at')
            })
        
        # Ordenar por número de cuenta
        result.sort(key=lambda x: x.get('account_number', 0))
        return result
    
    def switch_account(self, account_number: int) -> bool:
        """
        Cambia la cuenta activa
        
        Args:
            account_number: Número de cuenta a activar (1-5)
            
        Returns:
            True si se cambió correctamente, False en caso contrario
        """
        accounts = self._get_accounts_data()
        
        # Desactivar todas las cuentas
        for acc_data in accounts.values():
            acc_data['is_active'] = False
        
        # Activar la cuenta solicitada
        for acc_data in accounts.values():
            if acc_data.get('account_number') == account_number:
                acc_data['is_active'] = True
                self._save_accounts_data(accounts)
                log.info(f"Cuenta {account_number} activada")
                return True
        
        log.error(f"Cuenta {account_number} no encontrada")
        return False
    
    def remove_account(self, account_number: int) -> bool:
        """
        Elimina una cuenta
        
        Args:
            account_number: Número de cuenta a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        accounts = self._get_accounts_data()
        
        for acc_id, acc_data in list(accounts.items()):
            if acc_data.get('account_number') == account_number:
                del accounts[acc_id]
                self._save_accounts_data(accounts)
                log.info(f"Cuenta {account_number} eliminada")
                return True
        
        log.error(f"Cuenta {account_number} no encontrada")
        return False
    
    def get_active_account_token(self) -> Optional[str]:
        """
        Obtiene el token de acceso de la cuenta activa (cifrado)
        
        Returns:
            Token cifrado o None si no hay cuenta activa
        """
        account = self.get_account()
        if account:
            return account.get('encrypted_access_token')
        return None
    
    def update_account_token(
        self, 
        account_number: int,
        encrypted_access_token: str,
        encrypted_refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> bool:
        """
        Actualiza los tokens de una cuenta
        
        Args:
            account_number: Número de cuenta
            encrypted_access_token: Nuevo token de acceso cifrado
            encrypted_refresh_token: Nuevo token de refresco (opcional)
            expires_at: Nueva fecha de expiración (opcional)
            
        Returns:
            True si se actualizó correctamente
        """
        accounts = self._get_accounts_data()
        
        for acc_data in accounts.values():
            if acc_data.get('account_number') == account_number:
                acc_data['encrypted_access_token'] = encrypted_access_token
                if encrypted_refresh_token:
                    acc_data['encrypted_refresh_token'] = encrypted_refresh_token
                if expires_at:
                    acc_data['expires_at'] = expires_at
                acc_data['updated_at'] = datetime.utcnow().isoformat()
                self._save_accounts_data(accounts)
                return True
        
        return False

