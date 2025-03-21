"""
Client Entity

This module defines the Client entity for the federated learning system.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Client:
    """
    Client entity for the federated learning system.
    
    This class represents a client that participates in the federated learning process.
    """
    
    client_id: str
    """Unique identifier for the client."""
    
    name: str
    """Human-readable name of the client."""
    
    status: str = "active"
    """Current status of the client (active, inactive, etc.)."""
    
    capabilities: Dict[str, Any] = field(default_factory=dict)
    """Dictionary of client capabilities (e.g., CPU, memory, etc.)."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the client."""
    
    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the client was created."""
    
    last_seen_at: Optional[datetime] = None
    """Timestamp when the client was last seen."""
    
    def update_last_seen(self) -> None:
        """Update the last_seen_at timestamp to the current time."""
        self.last_seen_at = datetime.now()
    
    def update_status(self, status: str) -> None:
        """
        Update the client's status.
        
        Args:
            status: New status value
        """
        self.status = status
    
    def is_active(self, timeout_seconds: int = 300) -> bool:
        """
        Check if the client is active based on the last_seen_at timestamp.
        
        Args:
            timeout_seconds: Number of seconds after which a client is considered inactive
            
        Returns:
            True if the client is active, False otherwise
        """
        if not self.last_seen_at:
            return self.status == "active"
        
        time_difference = (datetime.now() - self.last_seen_at).total_seconds()
        return time_difference <= timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the client to a dictionary.
        
        Returns:
            Dictionary representation of the client
        """
        return {
            "client_id": self.client_id,
            "name": self.name,
            "status": self.status,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Client":
        """
        Create a client from a dictionary.
        
        Args:
            data: Dictionary representation of the client
            
        Returns:
            Client instance
        """
        client = cls(
            client_id=data["client_id"],
            name=data["name"],
            status=data.get("status", "active"),
            capabilities=data.get("capabilities", {}),
            metadata=data.get("metadata", {})
        )
        
        if "created_at" in data:
            client.created_at = datetime.fromisoformat(data["created_at"])
        
        if "last_seen_at" in data and data["last_seen_at"]:
            client.last_seen_at = datetime.fromisoformat(data["last_seen_at"])
        
        return client 