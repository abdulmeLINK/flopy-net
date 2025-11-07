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
Network Client Interface

This module defines the interface for network clients used throughout the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable


class INetworkClient(ABC):
    """
    Interface for network clients used throughout the system.
    
    A network client is responsible for handling network communication between components.
    This includes sending and receiving messages, and maintaining connections.
    """
    
    @abstractmethod
    def connect(self, endpoint: str, auth_token: Optional[str] = None) -> bool:
        """
        Connect to a remote endpoint.
        
        Args:
            endpoint: The URL or address of the remote endpoint
            auth_token: Optional authentication token
            
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the remote endpoint.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def send_message(self, destination: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to a destination.
        
        Args:
            destination: The destination endpoint
            message_type: Type of message being sent
            payload: Message payload as a dictionary
            
        Returns:
            Response from the destination as a dictionary
        """
        pass
    
    @abstractmethod
    def register_handler(self, message_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> bool:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Function that will handle messages of this type
            
        Returns:
            True if registration successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the network client.
        
        Returns:
            Dictionary with status information
        """
        pass 