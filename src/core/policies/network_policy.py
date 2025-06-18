"""
Network Policy

This module defines policies for software-defined networking in the system.
"""

from abc import abstractmethod
from typing import Dict, Any, List

from src.core.policies.policy import IPolicy


class INetworkPolicy(IPolicy):
    """
    Interface for network policies.
    
    Network policies determine routing, bandwidth allocation,
    and network topology in the software-defined network.
    """
    
    @abstractmethod
    def apply_routing(self, topology: Dict[str, Any], flows: List[Dict[str, Any]], 
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply routing rules to the network.
        
        Args:
            topology: Network topology description
            flows: Network flows to route
            context: Additional context for routing
            
        Returns:
            Dictionary with routing decisions
        """
        pass
    
    @abstractmethod
    def allocate_bandwidth(self, links: List[Dict[str, Any]], requests: List[Dict[str, Any]],
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Allocate bandwidth to network links.
        
        Args:
            links: Network links with capacities
            requests: Bandwidth allocation requests
            context: Additional context for allocation
            
        Returns:
            Dictionary with bandwidth allocation decisions
        """
        pass


class ShortestPathPolicy(INetworkPolicy):
    """
    Shortest path routing policy.
    
    This policy routes traffic through the shortest available path.
    """
    
    def __init__(self, policy_id: str, description: str = "Shortest path routing policy"):
        self.policy_id = policy_id
        self.policy_type = "network_routing"
        self.description = description
        self.parameters = {}
    
    def get_id(self) -> str:
        return self.policy_id
    
    def get_type(self) -> str:
        return self.policy_type
    
    def get_description(self) -> str:
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
                - topology: Network topology
                - flows: Network flows
                - requests: Bandwidth requests
                
        Returns:
            Dictionary with routing and bandwidth decisions
        """
        topology = context.get('topology', {})
        flows = context.get('flows', [])
        requests = context.get('requests', [])
        links = context.get('links', [])
        
        routing = self.apply_routing(topology, flows)
        bandwidth = self.allocate_bandwidth(links, requests)
        
        return {
            'routing': routing,
            'bandwidth': bandwidth,
            'policy_id': self.policy_id,
            'policy_type': self.policy_type
        }
    
    def apply_routing(self, topology: Dict[str, Any], flows: List[Dict[str, Any]], 
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply shortest path routing.
        
        Args:
            topology: Network topology description
            flows: Network flows to route
            context: Additional context for routing
            
        Returns:
            Dictionary with routing decisions
        """
        # Simple implementation using shortest path calculation
        # In a real implementation, this would use a graph algorithm
        
        routes = {}
        for flow in flows:
            source = flow.get('source')
            destination = flow.get('destination')
            flow_id = flow.get('flow_id')
            
            # Calculate shortest path (simplified)
            # In a real implementation, this would use Dijkstra's algorithm
            route = self._calculate_shortest_path(topology, source, destination)
            
            routes[flow_id] = {
                'path': route,
                'source': source,
                'destination': destination
            }
        
        return {
            'routes': routes
        }
    
    def allocate_bandwidth(self, links: List[Dict[str, Any]], requests: List[Dict[str, Any]],
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Allocate bandwidth proportionally.
        
        Args:
            links: Network links with capacities
            requests: Bandwidth allocation requests
            context: Additional context for allocation
            
        Returns:
            Dictionary with bandwidth allocation decisions
        """
        # Simple proportional bandwidth allocation
        allocations = {}
        
        for link in links:
            link_id = link.get('link_id')
            capacity = link.get('capacity', 0)
            
            # Find all requests for this link
            link_requests = [r for r in requests if r.get('link_id') == link_id]
            total_requested = sum(r.get('requested_bandwidth', 0) for r in link_requests)
            
            # Allocate proportionally if oversubscribed, otherwise give requested amount
            if total_requested > capacity and total_requested > 0:
                ratio = capacity / total_requested
                for request in link_requests:
                    request_id = request.get('request_id')
                    requested = request.get('requested_bandwidth', 0)
                    allocations[request_id] = requested * ratio
            else:
                for request in link_requests:
                    request_id = request.get('request_id')
                    requested = request.get('requested_bandwidth', 0)
                    allocations[request_id] = requested
        
        return {
            'allocations': allocations
        }
    
    def _calculate_shortest_path(self, topology: Dict[str, Any], source: str, destination: str) -> List[str]:
        """
        Calculate the shortest path between two nodes.
        
        This is a simplified implementation. In a real system, this would use
        a proper graph algorithm like Dijkstra's.
        
        Args:
            topology: Network topology
            source: Source node
            destination: Destination node
            
        Returns:
            List of nodes forming the path
        """
        # Simplified implementation - just returns direct path for now
        # In a real implementation, this would use a shortest path algorithm
        return [source, destination]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy
        """
        return {
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'description': self.description,
            'parameters': self.parameters
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ShortestPathPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            ShortestPathPolicy instance
        """
        policy = ShortestPathPolicy(
            policy_id=data['policy_id'],
            description=data.get('description', "Shortest path routing policy")
        )
        
        if 'parameters' in data:
            policy.parameters = data['parameters']
            
        return policy 