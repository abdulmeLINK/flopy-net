"""
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
Protocol definitions for SDN Flow Manager components.

This module defines Protocol classes that describe the interfaces expected
by mixins and components in the SDN flow management system.
"""

from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
import logging


@runtime_checkable
class SDNControllerProtocol(Protocol):
    """Protocol for SDN controller implementations used by flow mixins."""
    
    def get_switches(self) -> List[Dict[str, Any]]:
        """Get list of connected switches."""
        ...
    
    def add_flow(self, switch: Any, priority: int, match: Dict[str, Any], 
                 actions: List[Dict[str, Any]], idle_timeout: int = 0, 
                 hard_timeout: int = 0) -> bool:
        """Add a flow rule to a switch."""
        ...


@runtime_checkable
class PolicyEngineProtocol(Protocol):
    """Protocol for policy engine implementations."""
    
    def validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a policy and return validation result."""
        ...
    
    def authorize_flow(self, src_ip: str, dst_ip: str) -> bool:
        """Check if a flow between IPs is authorized."""
        ...


@runtime_checkable
class FlowRulesHost(Protocol):
    """
    Protocol defining requirements for classes using FlowRulesMixin.
    
    Classes that use FlowRulesMixin must provide these attributes
    to ensure the mixin methods can function correctly.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Logger instance for logging operations."""
        ...
    
    @property
    def sdn_controller(self) -> SDNControllerProtocol:
        """SDN controller for managing flows."""
        ...
    
    @property
    def policy_engine(self) -> PolicyEngineProtocol:
        """Policy engine for validating flow policies."""
        ...
    
    @property
    def flow_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Dictionary storing active flow rules by client/identifier."""
        ...
