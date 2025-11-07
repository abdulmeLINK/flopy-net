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
Client Manager Interface

This module defines the interface for client management services used in the
federated learning system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IClientManager(ABC):
    """
    Interface for client management services in the federated learning system.
    
    Client managers are responsible for registering, tracking, and managing
    federated learning clients throughout their lifecycle.
    """
    
    @abstractmethod
    def register_client(self, client_id: str, client_info: Dict[str, Any]) -> bool:
        """
        Register a new client with the system.
        
        Args:
            client_id: Unique identifier for the client
            client_info: Information about the client including capabilities
            
        Returns:
            True if registration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unregister_client(self, client_id: str) -> bool:
        """
        Unregister a client from the system.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if unregistration was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Client information dictionary or None if client not found
        """
        pass
    
    @abstractmethod
    def list_clients(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List all registered clients, optionally filtered.
        
        Args:
            filters: Optional filters to apply when listing clients
            
        Returns:
            List of client information dictionaries
        """
        pass
    
    @abstractmethod
    def update_client_status(self, client_id: str, status: str) -> bool:
        """
        Update the status of a client.
        
        Args:
            client_id: Unique identifier for the client
            status: New status for the client
            
        Returns:
            True if status update was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_client_metrics(self, client_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Dictionary of client metrics
        """
        pass
    
    @abstractmethod
    def select_clients(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Select a number of clients based on specific criteria.
        
        Args:
            count: Number of clients to select
            criteria: Optional selection criteria
            
        Returns:
            List of selected client IDs
        """
        pass 