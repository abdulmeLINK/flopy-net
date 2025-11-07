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