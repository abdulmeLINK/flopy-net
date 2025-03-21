"""
Federated Learning Server Interface

This module defines the interface for a federated learning server.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IFLServer(ABC):
    """Interface defining the contract for federated learning servers."""
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the server.
        
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the server."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current server status.
        
        Returns:
            A dictionary containing server status information
        """
        pass
    
    @abstractmethod
    def register_client(self, client_id: str, client_info: Dict[str, Any]) -> bool:
        """
        Register a client with the server.
        
        Args:
            client_id: Unique identifier for the client
            client_info: Information about the client
            
        Returns:
            True if registered successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the server.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if configured successfully, False otherwise
        """
        pass 