"""
Módulo de gestión de cuentas de Fortnite
Permite gestionar hasta 5 cuentas del owner
"""

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
        encrypted_refresh_token: str,
        account_id: str,
        display_name: str,
        token_expiry: str
    ) -> bool:
        """
        Agrega una nueva cuenta de Fortnite usando OAuth oficial
        Solo almacena refresh_token (encriptado), account_id, display_name y token_expiry
        
        Args:
            account_number: Número de cuenta (1-5)
            account_name: Nombre descriptivo de la cuenta
            encrypted_refresh_token: Token de refresco cifrado (único token almacenado)
            account_id: ID de la cuenta de Epic
            display_name: Nombre de visualización de Epic Games
            token_expiry: Fecha de expiración del refresh_token
            
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
                # Actualizar cuenta existente (solo campos OAuth)
                accounts[acc_id].update({
                    'account_name': account_name,
                    'encrypted_refresh_token': encrypted_refresh_token,
                    'account_id': account_id,
                    'display_name': display_name,
                    'token_expiry': token_expiry,
                    'updated_at': datetime.utcnow().isoformat(),
                    'auth_method': 'oauth'  # Marca de método de autenticación
                })
                # Eliminar campos obsoletos de DeviceAuth si existen
                accounts[acc_id].pop('encrypted_access_token', None)
                accounts[acc_id].pop('device_id', None)
                accounts[acc_id].pop('secret', None)
                accounts[acc_id].pop('user_agent', None)
                self._save_accounts_data(accounts)
                return True
        
        # Verificar límite de cuentas
        if len(accounts) >= MAX_ACCOUNTS:
            log.error(f"Límite de {MAX_ACCOUNTS} cuentas alcanzado")
            return False
        
        # Crear nueva cuenta (solo campos OAuth)
        account_data = {
            'account_number': account_number,
            'account_name': account_name,
            'encrypted_refresh_token': encrypted_refresh_token,  # Único token almacenado
            'account_id': account_id,
            'display_name': display_name,
            'token_expiry': token_expiry,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True,
            'auth_method': 'oauth'  # Método de autenticación usado
        }
        
        accounts[account_id] = account_data
        self._save_accounts_data(accounts)
        
        # Log de debugging para verificar que se guardó
        log.info(f"[DEBUG] Account saved to JSON - Account #: {account_number}, Account ID: {account_id}")
        log.info(f"[DEBUG] Saved data keys: {list(account_data.keys())}")
        log.info(f"[DEBUG] Has encrypted_refresh_token: {bool(account_data.get('encrypted_refresh_token'))}")
        log.info(f"[DEBUG] encrypted_refresh_token length: {len(account_data.get('encrypted_refresh_token', ''))}")
        
        # Verificar que realmente se guardó en el archivo
        verify_data = self._get_accounts_data()
        if account_id in verify_data:
            log.info(f"[DEBUG] VERIFIED: Account {account_id} exists in storage after save")
        else:
            log.error(f"[DEBUG] ERROR: Account {account_id} NOT found in storage after save!")
        
        log.info(f"Cuenta {account_number} ({account_name}) agregada correctamente con OAuth")
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
                'display_name': acc_data.get('display_name', 'N/A'),
                'is_active': acc_data.get('is_active', False),
                'token_expiry': acc_data.get('token_expiry', 'N/A'),
                'auth_method': acc_data.get('auth_method', 'unknown'),
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
    
    def get_active_account_refresh_token(self) -> Optional[str]:
        """
        Obtiene el refresh_token de la cuenta activa (cifrado)
        El access_token se obtiene dinámicamente usando refresh_token
        
        Returns:
            Refresh token cifrado o None si no hay cuenta activa
        """
        account = self.get_account()
        if account:
            return account.get('encrypted_refresh_token')
        return None
    
    def update_account_token(
        self, 
        account_number: int,
        encrypted_refresh_token: str,
        token_expiry: Optional[str] = None
    ) -> bool:
        """
        Actualiza el refresh_token de una cuenta
        
        Args:
            account_number: Número de cuenta
            encrypted_refresh_token: Nuevo refresh token cifrado
            token_expiry: Nueva fecha de expiración del refresh token (opcional)
            
        Returns:
            True si se actualizó correctamente
        """
        accounts = self._get_accounts_data()
        
        for acc_data in accounts.values():
            if acc_data.get('account_number') == account_number:
                acc_data['encrypted_refresh_token'] = encrypted_refresh_token
                if token_expiry:
                    acc_data['token_expiry'] = token_expiry
                acc_data['updated_at'] = datetime.utcnow().isoformat()
                # Eliminar campos obsoletos si existen
                acc_data.pop('encrypted_access_token', None)
                acc_data.pop('expires_at', None)
                self._save_accounts_data(accounts)
                return True
        
        return False
    
    def update_account_name(self, account_number: int, new_name: str) -> bool:
        """
        Actualiza el nombre descriptivo de una cuenta
        
        Args:
            account_number: Número de cuenta (1-5)
            new_name: Nuevo nombre descriptivo para la cuenta
            
        Returns:
            True si se actualizó correctamente, False si la cuenta no existe
        """
        if not new_name or len(new_name.strip()) == 0:
            log.error("Nombre de cuenta no puede estar vacío")
            return False
        
        if len(new_name) > 50:
            log.error("Nombre de cuenta demasiado largo (máximo 50 caracteres)")
            return False
        
        accounts = self._get_accounts_data()
        
        for acc_data in accounts.values():
            if acc_data.get('account_number') == account_number:
                old_name = acc_data.get('account_name', 'Sin nombre')
                acc_data['account_name'] = new_name.strip()
                acc_data['updated_at'] = datetime.utcnow().isoformat()
                self._save_accounts_data(accounts)
                log.info(f"Nombre de cuenta {account_number} actualizado: '{old_name}' -> '{new_name}'")
                return True
        
        log.error(f"Cuenta {account_number} no encontrada")
        return False

