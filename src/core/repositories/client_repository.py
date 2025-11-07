#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Client Repository Interface

This module defines the interface for client repositories used by the federated learning system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import threading

from src.core.clients.client import Client


class IClientRepository(ABC):
    """
    Interface for client repositories that store information about federated learning clients.
    """
    
    @abstractmethod
    def register_client(self, client_id: str, capabilities: Dict[str, Any]) -> bool:
        """
        Register a new client in the repository.
        
        Args:
            client_id: Unique identifier for the client
            capabilities: Client capabilities and characteristics
            
        Returns:
            True if registration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_client(self, client: Client) -> bool:
        """
        Add a client to the repository.
        
        Args:
            client: Client to add
            
        Returns:
            True if added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_client(self, client_id: str) -> Optional[Client]:
        """
        Get a client by ID.
        
        Args:
            client_id: ID of the client to get
            
        Returns:
            Client if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_client(self, client: Client) -> bool:
        """
        Update a client in the repository.
        
        Args:
            client: Updated client
            
        Returns:
            True if updated successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_client(self, client_id: str) -> bool:
        """
        Remove a client from the repository.
        
        Args:
            client_id: ID of the client to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_all_clients(self) -> List[Client]:
        """
        Get all clients in the repository.
        
        Returns:
            List of all clients
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all clients from the repository."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get the number of clients in the repository.
        
        Returns:
            Number of clients
        """
        pass


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
    
    def register_client(self, client_id: str, capabilities: Dict[str, Any]) -> bool:
        """
        Register a new client in the repository.
        
        Args:
            client_id: Unique identifier for the client
            capabilities: Client capabilities and characteristics
            
        Returns:
            True if registration was successful, False otherwise
        """
        with self.lock:
            if client_id in self.clients:
                self.logger.warning(f"Client {client_id} already exists")
                return False
            
            self.clients[client_id] = Client(client_id, capabilities)
            self.logger.debug(f"Added client {client_id}")
            return True
    
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