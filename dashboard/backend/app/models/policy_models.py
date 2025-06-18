from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyType(BaseModel):
    """Model for a policy type."""
    type_id: str
    name: str
    description: Optional[str] = None


class Policy(BaseModel):
    """Model for a policy."""
    policy_id: str
    name: str
    type_id: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    priority: Optional[int] = None
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PolicyCreate(BaseModel):
    """Model for creating a policy."""
    name: str
    type_id: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    priority: Optional[int] = None
    enabled: bool = True


class PolicyList(BaseModel):
    """Response model for listing policies."""
    policies: List[Policy]


class PolicyCheck(BaseModel):
    """Model for checking if an action is allowed by policies."""
    component: str
    action: str
    parameters: Optional[Dict[str, Any]] = None


class PolicyCheckResponse(BaseModel):
    """Response model for policy check."""
    allowed: bool
    reason: Optional[str] = None
    policy_id: Optional[str] = None 