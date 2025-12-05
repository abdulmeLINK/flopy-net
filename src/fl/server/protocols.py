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
Protocol definitions for FL Server components.

This module defines Protocol classes that describe the interfaces expected
by mixins and components. Using Protocols enables:
- Static type checking with mypy
- Clear documentation of required attributes/methods
- Better IDE support and autocompletion
- Adherence to SOLID principles (Interface Segregation, Dependency Inversion)
"""

from typing import Dict, Any, Protocol, runtime_checkable
import threading


@runtime_checkable
class PolicyClientProtocol(Protocol):
    """Protocol for policy client implementations."""
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if an action is allowed by policy."""
        ...
    
    def is_available(self) -> bool:
        """Check if policy client is available."""
        ...


@runtime_checkable
class PolicyEnforcementHost(Protocol):
    """
    Protocol defining requirements for classes using PolicyEnforcementMixin.
    
    Classes that use PolicyEnforcementMixin must implement this protocol
    to ensure all required attributes are available.
    """
    
    @property
    def config(self) -> Dict[str, Any]:
        """Server configuration dictionary."""
        ...
    
    @property
    def policy_client(self) -> PolicyClientProtocol:
        """Policy client instance for policy checks."""
        ...
    
    @property
    def strict_policy_mode(self) -> bool:
        """Whether to enforce strict policy mode."""
        ...
    
    @property
    def model(self) -> str:
        """Model name/identifier."""
        ...
    
    @property
    def dataset(self) -> str:
        """Dataset name/identifier."""
        ...
    
    @property
    def rounds(self) -> int:
        """Number of training rounds."""
        ...


@runtime_checkable
class TrainingControlHost(Protocol):
    """
    Protocol defining requirements for classes using TrainingControlMixin.
    """
    
    @property
    def config(self) -> Dict[str, Any]:
        """Server configuration dictionary."""
        ...
    
    @property
    def port(self) -> int:
        """Server port."""
        ...
    
    @property
    def address(self) -> str:
        """Server address."""
        ...
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check policy (provided by PolicyEnforcementMixin)."""
        ...
