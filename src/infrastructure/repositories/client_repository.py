"""
Client Repository Implementation

This module provides an implementation of the client repository interface.
"""
import logging
from typing import Dict, List, Optional
import threading

from src.domain.interfaces.client_repository import IClientRepository
from src.domain.entities.client import Client


class InMemoryClientRepository(IClientRepository):
    """
    In-memory implementation of the client repository.
    
    This repository stores clients in memory for easy access and management.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the repository.
        
        Args:
            logger: Optional logger
        """
        self.clients: Dict[str, Client] = {}
        self.lock = threading.RLock()
        self.logger = logger or logging.getLogger(__name__)
    
    def add_client(self, client: Client) -> bool:
        """
        Add a client to the repository.
        
        Args:
            client: Client to add
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            if client.client_id in self.clients:
                self.logger.warning(f"Client {client.client_id} already exists")
                return False
            
            self.clients[client.client_id] = client
            self.logger.debug(f"Added client {client.client_id}")
            return True
    
    def get_client(self, client_id: str) -> Optional[Client]:
        """
        Get a client by ID.
        
        Args:
            client_id: ID of the client to get
            
        Returns:
            Client if found, None otherwise
        """
        with self.lock:
            client = self.clients.get(client_id)
            if client:
                self.logger.debug(f"Retrieved client {client_id}")
            else:
                self.logger.debug(f"Client {client_id} not found")
            return client
    
    def update_client(self, client: Client) -> bool:
        """
        Update a client in the repository.
        
        Args:
            client: Updated client
            
        Returns:
            True if updated successfully, False otherwise
        """
        with self.lock:
            if client.client_id not in self.clients:
                self.logger.warning(f"Client {client.client_id} not found")
                return False
            
            self.clients[client.client_id] = client
            self.logger.debug(f"Updated client {client.client_id}")
            return True
    
    def remove_client(self, client_id: str) -> bool:
        """
        Remove a client from the repository.
        
        Args:
            client_id: ID of the client to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        with self.lock:
            if client_id not in self.clients:
                self.logger.warning(f"Client {client_id} not found")
                return False
            
            del self.clients[client_id]
            self.logger.debug(f"Removed client {client_id}")
            return True
    
    def get_all_clients(self) -> List[Client]:
        """
        Get all clients in the repository.
        
        Returns:
            List of all clients
        """
        with self.lock:
            clients = list(self.clients.values())
            self.logger.debug(f"Retrieved {len(clients)} clients")
            return clients
    
    def clear(self) -> None:
        """Clear all clients from the repository."""
        with self.lock:
            self.clients.clear()
            self.logger.debug("Cleared all clients")
    
    def count(self) -> int:
        """
        Get the number of clients in the repository.
        
        Returns:
            Number of clients
        """
        with self.lock:
            count = len(self.clients)
            self.logger.debug(f"Client count: {count}")
            return count 