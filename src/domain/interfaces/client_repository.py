"""
Client Repository Interface

This module defines the interface for a client repository.
"""
from typing import Dict, List, Any, Optional

from src.domain.entities.client import Client


class IClientRepository:
    """
    Interface for a client repository.
    
    The repository is responsible for storing and retrieving client information.
    """
    
    def add_client(self, client: Client) -> bool:
        """
        Add a client to the repository.
        
        Args:
            client: Client to add
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def remove_client(self, client_id: str) -> bool:
        """
        Remove a client from the repository.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def get_client(self, client_id: str) -> Optional[Client]:
        """
        Get a client from the repository.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client if found, None otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def update_client(self, client: Client) -> bool:
        """
        Update a client in the repository.
        
        Args:
            client: Updated client
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def get_all_clients(self) -> List[Client]:
        """
        Get all clients from the repository.
        
        Returns:
            List of clients
        """
        raise NotImplementedError("Method not implemented")
    
    def get_client_count(self) -> int:
        """
        Get the number of clients in the repository.
        
        Returns:
            Number of clients
        """
        raise NotImplementedError("Method not implemented")
    
    def add_client_update(self, client_id: str, update: Dict[str, Any]) -> bool:
        """
        Add a client update to the repository.
        
        Args:
            client_id: Client identifier
            update: Update data
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented")
    
    def get_client_updates(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Get updates for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of updates
        """
        raise NotImplementedError("Method not implemented")
    
    def get_all_updates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all updates from the repository.
        
        Returns:
            Dictionary of client_id -> updates
        """
        raise NotImplementedError("Method not implemented")
    
    def clear_updates(self, client_id: Optional[str] = None) -> bool:
        """
        Clear updates for a client or all clients.
        
        Args:
            client_id: Client identifier (None for all clients)
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Method not implemented") 