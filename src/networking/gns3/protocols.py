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
Protocol definitions for GNS3 components.

This module defines Protocol classes that describe the interfaces expected
by mixins and components in the GNS3 networking module.
"""

from typing import Dict, Any, List, Optional, Tuple, Protocol, runtime_checkable
import logging


@runtime_checkable
class GNS3APIProtocol(Protocol):
    """Protocol for GNS3 API client implementations."""
    
    def get_nodes(self, project_id: str) -> Tuple[bool, Any]:
        """Get all nodes in a project."""
        ...
    
    def create_node(self, project_id: str, node_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a node in a project."""
        ...
    
    def create_link(self, project_id: str, node1_id: str, adapter1: int, port1: int,
                    node2_id: str, adapter2: int, port2: int) -> Tuple[bool, Any]:
        """Create a link between two nodes."""
        ...
    
    def send_vpcs_command(self, project_id: str, node_id: str, command: str) -> Tuple[bool, str]:
        """Send a command to a VPCS node."""
        ...


@runtime_checkable
class TopologyBuilderHost(Protocol):
    """
    Protocol defining requirements for classes using TopologyBuilderMixin.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Logger instance."""
        ...
    
    @property
    def api(self) -> GNS3APIProtocol:
        """GNS3 API client."""
        ...
    
    @property
    def project_id(self) -> str:
        """Current GNS3 project ID."""
        ...
    
    @property
    def templates(self) -> List[Dict[str, Any]]:
        """Available GNS3 templates."""
        ...
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name."""
        ...


@runtime_checkable
class HostOperationsHost(Protocol):
    """
    Protocol defining requirements for classes using HostOperationsMixin.
    """
    
    @property
    def api(self) -> GNS3APIProtocol:
        """GNS3 API client."""
        ...
    
    @property
    def project_id(self) -> str:
        """Current GNS3 project ID."""
        ...
    
    @property
    def topology_creator(self) -> Any:
        """Topology creator instance."""
        ...
    
    def get_node_ip(self, node_name: str) -> Optional[str]:
        """Get IP address for a node by name."""
        ...


@runtime_checkable
class NodeCreationHost(Protocol):
    """
    Protocol defining requirements for classes using NodeCreationMixin.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Logger instance."""
        ...
    
    @property
    def gns3_manager(self) -> Any:
        """GNS3 manager with API attribute."""
        ...
    
    @property
    def topology(self) -> Dict[str, Any]:
        """Topology configuration with 'nodes' list."""
        ...
    
    @property
    def node_ids(self) -> Dict[str, str]:
        """Mapping of node names to their IDs."""
        ...


@runtime_checkable
class ComponentDeploymentHost(Protocol):
    """
    Protocol defining requirements for classes using ComponentDeploymentMixin.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Logger instance."""
        ...
    
    @property
    def simulator(self) -> Any:
        """Network simulator instance."""
        ...
    
    @property
    def config(self) -> Dict[str, Any]:
        """Scenario configuration."""
        ...
    
    @property
    def scenario_id(self) -> str:
        """Unique scenario identifier."""
        ...
    
    @property
    def project_name(self) -> str:
        """GNS3 project name."""
        ...
