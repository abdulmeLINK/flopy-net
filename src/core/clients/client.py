"""
Client Entity

This module defines the Client entity used throughout the federated learning system.
"""

from typing import Dict, Any, Optional, List


class Client:
    """
    Represents a federated learning client in the system.
    
    A client is a participant in the federated learning process that has
    local data and can perform training locally.
    """
    
    def __init__(self, client_id: str, capabilities: Dict[str, Any] = None):
        """
        Initialize a client.
        
        Args:
            client_id: Unique identifier for the client
            capabilities: Client capabilities and characteristics
        """
        self.client_id = client_id
        self.capabilities = capabilities or {}
        self.status = "registered"
        self.active = False
        self.metrics = {}
        self.round_participation = []
        
    def update_status(self, status: str) -> None:
        """
        Update the client's status.
        
        Args:
            status: New status
        """
        self.status = status
        
    def activate(self) -> None:
        """
        Activate the client.
        """
        self.active = True
        self.status = "active"
        
    def deactivate(self) -> None:
        """
        Deactivate the client.
        """
        self.active = False
        self.status = "inactive"
        
    def update_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """
        Update the client's capabilities.
        
        Args:
            capabilities: New capabilities
        """
        self.capabilities.update(capabilities)
        
    def record_round_participation(self, round_number: int, metrics: Dict[str, Any]) -> None:
        """
        Record the client's participation in a training round.
        
        Args:
            round_number: Round number
            metrics: Metrics from this round
        """
        self.round_participation.append({
            "round": round_number,
            "metrics": metrics
        })
        
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update the client's metrics.
        
        Args:
            metrics: New metrics
        """
        self.metrics.update(metrics)
        
    def get_participation_history(self) -> List[Dict[str, Any]]:
        """
        Get the client's participation history.
        
        Returns:
            List of round participation records
        """
        return self.round_participation
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the client to a dictionary.
        
        Returns:
            Dictionary representation of the client
        """
        return {
            "client_id": self.client_id,
            "capabilities": self.capabilities,
            "status": self.status,
            "active": self.active,
            "metrics": self.metrics,
            "round_participation": self.round_participation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Client':
        """
        Create a client from a dictionary.
        
        Args:
            data: Dictionary representation of a client
            
        Returns:
            Client instance
        """
        client = cls(data["client_id"], data.get("capabilities", {}))
        client.status = data.get("status", "registered")
        client.active = data.get("active", False)
        client.metrics = data.get("metrics", {})
        client.round_participation = data.get("round_participation", [])
        return client 