"""
Network Client Interface

This module defines the interface for network communication clients used
by components in the federated learning system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable


class INetworkClient(ABC):
    """
    Interface for network communication clients.
    
    This interface defines methods for components to communicate with each other
    over the network, either directly or through the policy engine.
    """
    
    @abstractmethod
    def connect(self, endpoint: str, auth_token: Optional[str] = None) -> bool:
        """
        Connect to a remote endpoint.
        
        Args:
            endpoint: The endpoint to connect to (URL or address)
            auth_token: Optional authentication token
            
        Returns:
            True if connected successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the remote endpoint.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def send_message(self, destination: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to a destination.
        
        Args:
            destination: Destination identifier (component name, URL, etc.)
            message_type: Type of message being sent
            payload: Message payload
            
        Returns:
            Response from the destination
        """
        pass
    
    @abstractmethod
    def register_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Register a message handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Function to call when a message of this type is received
            
        Returns:
            True if registered successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check with the policy engine if an action is allowed.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Policy evaluation result
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the network client.
        
        Returns:
            Dictionary containing status information
        """
        pass 