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
Federated Learning Model Entity

This module defines the FLModel entity for the federated learning system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class FLModel:
    """
    Federated Learning Model entity.
    
    This class represents a model in the federated learning system.
    """
    
    name: str
    """Name of the model."""
    
    weights: List[Any] = field(default_factory=list)
    """Model weights or parameters."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the model."""
    
    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the model was created."""
    
    updated_at: Optional[datetime] = None
    """Timestamp when the model was last updated."""
    
    def update_weights(self, weights: List[Any]) -> None:
        """
        Update the model weights.
        
        Args:
            weights: New model weights
        """
        self.weights = weights
        self.updated_at = datetime.now()
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update the model metadata.
        
        Args:
            metadata: New model metadata
        """
        self.metadata.update(metadata)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            "name": self.name,
            "weights": self.weights,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FLModel":
        """
        Create a model from a dictionary.
        
        Args:
            data: Dictionary representation of the model
            
        Returns:
            FLModel instance
        """
        model = cls(
            name=data["name"],
            weights=data.get("weights", []),
            metadata=data.get("metadata", {})
        )
        
        if "created_at" in data:
            model.created_at = datetime.fromisoformat(data["created_at"])
        
        if "updated_at" in data and data["updated_at"]:
            model.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return model 