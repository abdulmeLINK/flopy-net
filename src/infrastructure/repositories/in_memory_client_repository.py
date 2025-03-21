"""
In-Memory Client Repository

This module provides an in-memory implementation of the client repository.
"""
import logging
from typing import Dict, List, Any, Optional

from src.domain.interfaces.client_repository import IClientRepository
from src.domain.entities.client import Client


class InMemoryClientRepository(IClientRepository):
    """
    In-memory implementation of the client repository.
    
    This class stores client information in memory for testing purposes.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the in-memory client repository.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.clients = {}  # Dictionary of client_id -> Client
        self.client_updates = {}  # Dictionary of client_id -> updates
    
    def add_client(self, client: Client) -> bool:
        """
        Add a client to the repository.
        
        Args:
            client: Client to add
            
        Returns:
            True if successful, False otherwise
        """
        if client.client_id in self.clients:
            self.logger.warning(f"Client {client.client_id} already exists")
            return False
        
        self.clients[client.client_id] = client
        self.logger.info(f"Added client {client.client_id}")
        return True
    
    def remove_client(self, client_id: str) -> bool:
        """
        Remove a client from the repository.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if successful, False otherwise
        """
        if client_id not in self.clients:
            self.logger.warning(f"Client {client_id} not found")
            return False
        
        del self.clients[client_id]
        if client_id in self.client_updates:
            del self.client_updates[client_id]
        
        self.logger.info(f"Removed client {client_id}")
        return True
    
    def get_client(self, client_id: str) -> Optional[Client]:
        """
        Get a client from the repository.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client if found, None otherwise
        """
        client = self.clients.get(client_id)
        if not client:
            self.logger.warning(f"Client {client_id} not found")
            return None
        
        return client
    
    def update_client(self, client: Client) -> bool:
        """
        Update a client in the repository.
        
        Args:
            client: Updated client
            
        Returns:
            True if successful, False otherwise
        """
        if client.client_id not in self.clients:
            self.logger.warning(f"Client {client.client_id} not found")
            return False
        
        self.clients[client.client_id] = client
        self.logger.info(f"Updated client {client.client_id}")
        return True
    
    def get_all_clients(self) -> List[Client]:
        """
        Get all clients from the repository.
        
        Returns:
            List of clients
        """
        return list(self.clients.values())
    
    def get_client_count(self) -> int:
        """
        Get the number of clients in the repository.
        
        Returns:
            Number of clients
        """
        return len(self.clients)
    
    def add_client_update(self, client_id: str, update: Dict[str, Any]) -> bool:
        """
        Add a client update to the repository.
        
        Args:
            client_id: Client identifier
            update: Update data
            
        Returns:
            True if successful, False otherwise
        """
        if client_id not in self.clients:
            self.logger.warning(f"Client {client_id} not found")
            return False
        
        if client_id not in self.client_updates:
            self.client_updates[client_id] = []
        
        self.client_updates[client_id].append(update)
        self.logger.info(f"Added update for client {client_id}")
        return True
    
    def get_client_updates(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Get updates for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of updates
        """
        if client_id not in self.clients:
            self.logger.warning(f"Client {client_id} not found")
            return []
        
        return self.client_updates.get(client_id, [])
    
    def get_all_updates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all updates from the repository.
        
        Returns:
            Dictionary of client_id -> updates
        """
        return self.client_updates
    
    def clear_updates(self, client_id: Optional[str] = None) -> bool:
        """
        Clear updates for a client or all clients.
        
        Args:
            client_id: Client identifier (None for all clients)
            
        Returns:
            True if successful, False otherwise
        """
        if client_id:
            if client_id not in self.clients:
                self.logger.warning(f"Client {client_id} not found")
                return False
            
            if client_id in self.client_updates:
                self.client_updates[client_id] = []
                self.logger.info(f"Cleared updates for client {client_id}")
        else:
            # Clear all updates
            self.client_updates = {}
            self.logger.info("Cleared all client updates")
        
        return True 