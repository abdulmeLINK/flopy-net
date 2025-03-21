"""
Mock Network Simulator

This module provides a mock implementation of the network simulator.
"""
import logging
import random
from typing import Dict, Any, List, Optional

from src.domain.interfaces.network_simulator import INetworkSimulator


class MockNetworkSimulator(INetworkSimulator):
    """
    Mock implementation of the network simulator.
    
    This class simulates network behavior for testing and development purposes.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the mock network simulator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.topology = {}
        self.clients = {}
        self.links = {}
        self.metrics = {
            "ping": {},
            "bandwidth": {},
            "congestion": {
                "congestion_level": 0.0,
                "congested_links": []
            }
        }
    
    def create_topology(self, topology_config: Dict[str, Any]) -> bool:
        """
        Create a network topology.
        
        Args:
            topology_config: Topology configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating mock network topology")
            self.topology = topology_config
            
            # Extract links from topology config
            self.links = {}
            for link in topology_config.get("links", []):
                source = link.get("source")
                target = link.get("target")
                if source and target:
                    link_id = f"{source}-{target}"
                    self.links[link_id] = link.copy()
                    
                    # Initialize metrics for this link
                    bandwidth = link.get("bandwidth", 100)
                    delay = link.get("delay", "5ms")
                    delay_ms = int(delay.replace("ms", "")) if isinstance(delay, str) else delay
                    
                    self.metrics["ping"][link_id] = {
                        "min_ms": delay_ms * 0.8,
                        "avg_ms": delay_ms,
                        "max_ms": delay_ms * 1.2,
                        "loss_percent": link.get("loss", 0) * 100
                    }
                    
                    self.metrics["bandwidth"][link_id] = {
                        "bandwidth_mbps": bandwidth,
                        "utilization_percent": random.uniform(10, 30)
                    }
            
            self.logger.info(f"Created topology with {len(self.links)} links")
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating topology: {e}")
            return False
    
    def start_simulation(self) -> bool:
        """
        Start the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Starting mock network simulation")
        self.running = True
        return True
    
    def stop_simulation(self) -> bool:
        """
        Stop the network simulation.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Stopping mock network simulation")
        self.running = False
        return True
    
    def add_client_node(self, client_id: str, client_config: Dict[str, Any]) -> bool:
        """
        Add a client node to the simulation.
        
        Args:
            client_id: Client identifier
            client_config: Client configuration
            
        Returns:
            True if successful, False otherwise
        """
        if client_id in self.clients:
            self.logger.warning(f"Client {client_id} already exists")
            return False
        
        self.clients[client_id] = client_config
        
        # Connect client to a host if specified
        host = client_config.get("host")
        if host:
            self.logger.info(f"Connected client {client_id} to host {host}")
        
        return True
    
    def remove_client_node(self, client_id: str) -> bool:
        """
        Remove a client node from the simulation.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if successful, False otherwise
        """
        if client_id not in self.clients:
            self.logger.warning(f"Client {client_id} does not exist")
            return False
        
        del self.clients[client_id]
        self.logger.info(f"Removed client {client_id}")
        return True
    
    def set_link_bandwidth(self, source: str, target: str, bandwidth: float) -> bool:
        """
        Set the bandwidth for a link.
        
        Args:
            source: Source node
            target: Target node
            bandwidth: Bandwidth in Mbps
            
        Returns:
            True if successful, False otherwise
        """
        link_id = f"{source}-{target}"
        if link_id not in self.links:
            link_id = f"{target}-{source}"
            if link_id not in self.links:
                self.logger.warning(f"Link {source}-{target} does not exist")
                return False
        
        self.links[link_id]["bandwidth"] = bandwidth
        
        # Update metrics
        self.metrics["bandwidth"][link_id] = {
            "bandwidth_mbps": bandwidth,
            "utilization_percent": self.metrics["bandwidth"].get(link_id, {}).get("utilization_percent", 20)
        }
        
        self.logger.info(f"Set bandwidth for link {link_id} to {bandwidth} Mbps")
        return True
    
    def add_link_delay(self, source: str, target: str, delay: Any) -> bool:
        """
        Add delay to a link.
        
        Args:
            source: Source node
            target: Target node
            delay: Delay in ms or as string (e.g., "10ms")
            
        Returns:
            True if successful, False otherwise
        """
        link_id = f"{source}-{target}"
        if link_id not in self.links:
            link_id = f"{target}-{source}"
            if link_id not in self.links:
                self.logger.warning(f"Link {source}-{target} does not exist")
                return False
        
        delay_ms = int(delay.replace("ms", "")) if isinstance(delay, str) else delay
        self.links[link_id]["delay"] = f"{delay_ms}ms"
        
        # Update metrics
        self.metrics["ping"][link_id] = {
            "min_ms": delay_ms * 0.8,
            "avg_ms": delay_ms,
            "max_ms": delay_ms * 1.2,
            "loss_percent": self.metrics["ping"].get(link_id, {}).get("loss_percent", 0)
        }
        
        self.logger.info(f"Added {delay_ms}ms delay to link {link_id}")
        return True
    
    def add_link_loss(self, source: str, target: str, loss: float) -> bool:
        """
        Add packet loss to a link.
        
        Args:
            source: Source node
            target: Target node
            loss: Loss rate (0.0 to 1.0)
            
        Returns:
            True if successful, False otherwise
        """
        link_id = f"{source}-{target}"
        if link_id not in self.links:
            link_id = f"{target}-{source}"
            if link_id not in self.links:
                self.logger.warning(f"Link {source}-{target} does not exist")
                return False
        
        self.links[link_id]["loss"] = loss
        
        # Update metrics
        self.metrics["ping"][link_id]["loss_percent"] = loss * 100
        
        # If loss is 100%, add this to congested links
        if loss >= 1.0:
            if link_id not in [link["id"] for link in self.metrics["congestion"]["congested_links"]]:
                self.metrics["congestion"]["congested_links"].append({
                    "id": link_id,
                    "utilization": 100.0,
                    "status": "failed"
                })
            self._update_congestion_level()
        
        self.logger.info(f"Added {loss*100}% packet loss to link {link_id}")
        return True
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the network.
        
        Returns:
            Dictionary containing performance metrics
        """
        # Update utilization metrics with some randomness
        for link_id in self.metrics["bandwidth"]:
            current_util = self.metrics["bandwidth"][link_id]["utilization_percent"]
            # Add some random variation (-5% to +5%)
            new_util = max(0, min(100, current_util + random.uniform(-5, 5)))
            self.metrics["bandwidth"][link_id]["utilization_percent"] = new_util
            
            # Check for congestion
            if new_util > 80:
                # Add to congested links if not already there
                if link_id not in [link["id"] for link in self.metrics["congestion"]["congested_links"]]:
                    self.metrics["congestion"]["congested_links"].append({
                        "id": link_id,
                        "utilization": new_util,
                        "status": "congested"
                    })
            else:
                # Remove from congested links if there
                self.metrics["congestion"]["congested_links"] = [
                    link for link in self.metrics["congestion"]["congested_links"] 
                    if link["id"] != link_id or link["status"] == "failed"
                ]
            
        # Update congestion level
        self._update_congestion_level()
        
        return self.metrics
    
    def _update_congestion_level(self) -> None:
        """Update the overall congestion level based on congested links."""
        congested_links = self.metrics["congestion"]["congested_links"]
        if congested_links:
            self.metrics["congestion"]["congestion_level"] = sum(link.get("utilization", 0) for link in congested_links) / len(congested_links) / 100.0
        else:
            self.metrics["congestion"]["congestion_level"] = 0.0
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get the current status of the simulation.
        
        Returns:
            Dictionary containing simulation status information
        """
        return {
            "running": self.running,
            "clients": len(self.clients),
            "links": len(self.links),
            "congestion_level": self.metrics["congestion"]["congestion_level"]
        }
    
    def save_simulation_state(self, file_path: str) -> bool:
        """
        Save the current simulation state to a file.
        
        Args:
            file_path: Path to save the simulation state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            state = {
                "topology": self.topology,
                "clients": self.clients,
                "links": self.links,
                "metrics": self.metrics,
                "running": self.running
            }
            
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=2)
                
            self.logger.info(f"Saved simulation state to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving simulation state: {e}")
            return False
    
    def load_simulation_state(self, file_path: str) -> bool:
        """
        Load a simulation state from a file.
        
        Args:
            file_path: Path to load the simulation state from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            import os
            
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return False
                
            with open(file_path, 'r') as f:
                state = json.load(f)
                
            self.topology = state.get("topology", {})
            self.clients = state.get("clients", {})
            self.links = state.get("links", {})
            self.metrics = state.get("metrics", {
                "ping": {},
                "bandwidth": {},
                "congestion": {
                    "congestion_level": 0.0,
                    "congested_links": []
                }
            })
            self.running = state.get("running", False)
            
            self.logger.info(f"Loaded simulation state from {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading simulation state: {e}")
            return False 