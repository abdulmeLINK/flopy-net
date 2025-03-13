from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field


class Condition(BaseModel):
    """Model representing a policy condition."""
    field: str
    operator: str
    value: Any


class Action(BaseModel):
    """Model representing a policy action."""
    type: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Policy(BaseModel):
    """Model representing a complete policy."""
    policy_id: str
    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    actions: List[Action]
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        schema_extra = {
            "example": {
                "policy_id": "net_opt_001",
                "name": "High Latency Rerouting",
                "description": "Reroute traffic when latency exceeds threshold",
                "conditions": [
                    {
                        "field": "latency",
                        "operator": ">",
                        "value": 50
                    }
                ],
                "actions": [
                    {
                        "type": "sdn",
                        "target": "reroute",
                        "parameters": {
                            "priority": "high"
                        }
                    }
                ],
                "priority": 10,
                "enabled": True,
                "tags": ["networking", "optimization"]
            }
        }


class PolicyCreate(BaseModel):
    """Model for policy creation requests."""
    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    actions: List[Action]
    priority: int = 0
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)


class PolicyUpdate(BaseModel):
    """Model for policy update requests."""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[Condition]] = None
    actions: Optional[List[Action]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class PolicyResponse(BaseModel):
    """Model for policy responses."""
    policy_id: str
    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    actions: List[Action]
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[str]


class PoliciesResponse(BaseModel):
    """Model for multiple policies response."""
    items: List[PolicyResponse]
    total: int 