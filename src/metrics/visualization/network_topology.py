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
Network topology visualization module for federated learning systems.
This module provides visualization of the federated learning network structure.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import math

logger = logging.getLogger(__name__)


class NetworkTopologyVisualizer:
    """
    Network topology visualization for federated learning systems.
    
    This visualizer creates representations of the network structure, showing:
    - Server-client relationships
    - Connection status and quality
    - Client geographical distribution
    - Network performance metrics
    """
    
    def __init__(
        self,
        output_dir: str = "visualizations/network",
        layout_algorithm: str = "force_directed",
        include_metrics: bool = True
    ):
        """
        Initialize the network topology visualizer.
        
        Args:
            output_dir: Directory to store visualization outputs
            layout_algorithm: Algorithm to use for node layout ('force_directed', 'circular', 'hierarchical')
            include_metrics: Whether to include performance metrics in visualization
        """
        self.output_dir = output_dir
        self.layout_algorithm = layout_algorithm
        self.include_metrics = include_metrics
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.supported_algorithms = ["force_directed", "circular", "hierarchical", "geographic"]
        if self.layout_algorithm not in self.supported_algorithms:
            logger.warning("Unsupported layout algorithm: %s, falling back to force_directed", layout_algorithm)
            self.layout_algorithm = "force_directed"
        
        logger.info("Network topology visualizer initialized with %s layout", self.layout_algorithm)
    
    def generate_visualization(self, topology_data: Dict[str, Any], output_file: str = "network_topology.json") -> str:
        """
        Generate network topology visualization from topology data.
        
        Args:
            topology_data: Network topology data containing nodes and edges
            output_file: Name of output file
            
        Returns:
            Path to the generated visualization file
        """
        # Apply layout algorithm to position nodes
        visualization = self._apply_layout(topology_data)
        
        # Add visual styling
        visualization = self._add_visual_styling(visualization)
        
        # Add performance metrics if requested
        if self.include_metrics:
            visualization = self._add_performance_metrics(visualization, topology_data)
        
        # Write visualization to file
        output_path = os.path.join(self.output_dir, output_file)
        with open(output_path, "w") as f:
            json.dump(visualization, f, indent=2)
        
        logger.info("Network topology visualization generated at %s", output_path)
        return output_path
    
    def _apply_layout(self, topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply layout algorithm to position nodes.
        
        Args:
            topology_data: Network topology data
            
        Returns:
            Visualization data with node positions
        """
        nodes = topology_data.get("nodes", [])
        edges = topology_data.get("edges", [])
        
        # Create a visualization object with positioned nodes
        visualization = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "layout_algorithm": self.layout_algorithm,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        }
        
        # Convert topology nodes to visualization nodes with positions
        if self.layout_algorithm == "force_directed":
            visualization["nodes"] = self._force_directed_layout(nodes, edges)
        elif self.layout_algorithm == "circular":
            visualization["nodes"] = self._circular_layout(nodes)
        elif self.layout_algorithm == "hierarchical":
            visualization["nodes"] = self._hierarchical_layout(nodes, edges)
        elif self.layout_algorithm == "geographic":
            visualization["nodes"] = self._geographic_layout(nodes)
        
        # Convert topology edges to visualization edges
        for edge in edges:
            visualization["edges"].append({
                "id": f"{edge.get('source')}-{edge.get('target')}",
                "source": edge.get("source"),
                "target": edge.get("target"),
                "status": edge.get("status", "unknown"),
                "latency": edge.get("latency_ms", 0)
            })
        
        return visualization
    
    def _force_directed_layout(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply force-directed layout algorithm to position nodes.
        
        Args:
            nodes: List of nodes
            edges: List of edges
            
        Returns:
            Nodes with position information
        """
        # Simple force-directed layout implementation
        # In a real implementation, this would use a more sophisticated algorithm
        
        # Initialize node positions randomly in a circle
        node_count = len(nodes)
        positioned_nodes = []
        
        # Place server node at the center
        server_index = None
        for i, node in enumerate(nodes):
            if node.get("type") == "server":
                server_index = i
                break
        
        for i, node in enumerate(nodes):
            node_type = node.get("type", "unknown")
            
            if i == server_index:
                # Server at center
                x, y = 0, 0
            else:
                # Clients in a circle around the server
                angle = (2 * math.pi * i) / (node_count - 1 if server_index is not None else node_count)
                radius = 500  # Arbitrary radius
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
            
            positioned_nodes.append({
                "id": node.get("id"),
                "label": node.get("id"),
                "type": node_type,
                "x": x,
                "y": y,
                "info": node.get("info", {})
            })
        
        return positioned_nodes
    
    def _circular_layout(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply circular layout algorithm to position nodes.
        
        Args:
            nodes: List of nodes
            
        Returns:
            Nodes with position information
        """
        # Position nodes in a circle
        node_count = len(nodes)
        positioned_nodes = []
        
        # Find server node (to place in center)
        server_indices = []
        for i, node in enumerate(nodes):
            if node.get("type") == "server":
                server_indices.append(i)
        
        radius = 500  # Arbitrary radius
        for i, node in enumerate(nodes):
            node_type = node.get("type", "unknown")
            
            if i in server_indices:
                # Server at center
                x, y = 0, 0
            else:
                # Calculate position in circle, adjusting for server nodes
                client_index = i - sum(1 for idx in server_indices if idx < i)
                client_count = node_count - len(server_indices)
                angle = (2 * math.pi * client_index) / client_count
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
            
            positioned_nodes.append({
                "id": node.get("id"),
                "label": node.get("id"),
                "type": node_type,
                "x": x,
                "y": y,
                "info": node.get("info", {})
            })
        
        return positioned_nodes
    
    def _hierarchical_layout(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply hierarchical layout algorithm to position nodes.
        
        Args:
            nodes: List of nodes
            edges: List of edges
            
        Returns:
            Nodes with position information
        """
        # Simple hierarchical layout with server at top
        positioned_nodes = []
        
        # Separate servers and clients
        servers = [node for node in nodes if node.get("type") == "server"]
        clients = [node for node in nodes if node.get("type") != "server"]
        
        # Position servers at the top
        server_count = len(servers)
        for i, server in enumerate(servers):
            x = (i - server_count / 2) * 300
            y = -300
            
            positioned_nodes.append({
                "id": server.get("id"),
                "label": server.get("id"),
                "type": server.get("type", "server"),
                "x": x,
                "y": y,
                "info": server.get("info", {})
            })
        
        # Position clients below in multiple rows
        client_count = len(clients)
        clients_per_row = min(10, max(5, math.ceil(math.sqrt(client_count))))
        
        for i, client in enumerate(clients):
            row = i // clients_per_row
            col = i % clients_per_row
            
            x = (col - clients_per_row / 2) * 200
            y = 100 + row * 200
            
            positioned_nodes.append({
                "id": client.get("id"),
                "label": client.get("id"),
                "type": client.get("type", "client"),
                "x": x,
                "y": y,
                "info": client.get("info", {})
            })
        
        return positioned_nodes
    
    def _geographic_layout(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply geographic layout based on node location data.
        
        Args:
            nodes: List of nodes
            
        Returns:
            Nodes with position information
        """
        # Simple geographic layout based on region coordinates
        # In a real implementation, this would use actual geographic coordinates
        
        # Define approximate positions for regions
        region_positions = {
            "US": (200, 200),
            "EU": (600, 150),
            "APAC": (900, 300),
            "LATAM": (300, 500),
            "MENA": (650, 350),
            "UNKNOWN": (500, 300)
        }
        
        # Add some randomness to positions within each region
        positioned_nodes = []
        for node in nodes:
            node_type = node.get("type", "unknown")
            
            if node_type == "server":
                # Server at center
                x, y = 500, 300
            else:
                # Get region from node info
                region = "UNKNOWN"
                if "info" in node and "region" in node["info"]:
                    region = node["info"]["region"]
                
                if region not in region_positions:
                    region = "UNKNOWN"
                
                # Get base position for region and add randomness
                base_x, base_y = region_positions[region]
                x = base_x + np.random.uniform(-50, 50)
                y = base_y + np.random.uniform(-50, 50)
            
            positioned_nodes.append({
                "id": node.get("id"),
                "label": node.get("id"),
                "type": node_type,
                "x": x,
                "y": y,
                "region": node.get("info", {}).get("region", "UNKNOWN"),
                "info": node.get("info", {})
            })
        
        return positioned_nodes
    
    def _add_visual_styling(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add visual styling to nodes and edges.
        
        Args:
            visualization: Visualization data
            
        Returns:
            Visualization data with styling
        """
        # Add styling to nodes
        for node in visualization["nodes"]:
            node_type = node.get("type", "unknown")
            
            if node_type == "server":
                node["size"] = 30
                node["color"] = "#FF5733"  # Orange-red for server
                node["shape"] = "diamond"
            else:
                node["size"] = 15
                
                # Color clients by region if available
                if "region" in node:
                    region_colors = {
                        "US": "#3366CC",  # Blue
                        "EU": "#33CC33",  # Green
                        "APAC": "#CC33CC",  # Purple
                        "LATAM": "#CCCC33",  # Yellow
                        "MENA": "#CC6633",  # Orange
                        "UNKNOWN": "#999999"  # Gray
                    }
                    node["color"] = region_colors.get(node["region"], "#999999")
                else:
                    node["color"] = "#3388FF"  # Default blue
                
                node["shape"] = "circle"
            
            # Add border
            node["borderWidth"] = 2
            node["borderColor"] = "#000000"
        
        # Add styling to edges
        for edge in visualization["edges"]:
            status = edge.get("status", "unknown")
            latency = edge.get("latency", 0)
            
            # Set color based on status
            if status == "active":
                edge["color"] = "#00FF00"  # Green for active
                edge["width"] = 3
            elif status == "slow":
                edge["color"] = "#FFFF00"  # Yellow for slow
                edge["width"] = 2
            elif status == "inactive":
                edge["color"] = "#FF0000"  # Red for inactive
                edge["width"] = 1
            else:
                edge["color"] = "#999999"  # Gray for unknown
                edge["width"] = 1
            
            # Add latency as label
            edge["label"] = f"{latency}ms"
            
            # Add dashes for high latency
            if latency > 100:
                edge["dashes"] = [5, 5]  # Dashed line for high latency
        
        return visualization
    
    def _add_performance_metrics(self, visualization: Dict[str, Any], topology_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add performance metrics to the visualization.
        
        Args:
            visualization: Visualization data
            topology_data: Network topology data
            
        Returns:
            Visualization data with performance metrics
        """
        # Extract metrics
        node_metrics = {}
        
        # Add node-specific metrics
        for node in topology_data.get("nodes", []):
            node_id = node.get("id")
            if node_id and "info" in node:
                info = node.get("info", {})
                metrics = {}
                
                # Extract relevant metrics from node info
                if "training_time_ms" in info:
                    metrics["training_time_ms"] = info["training_time_ms"]
                if "data_samples" in info:
                    metrics["data_samples"] = info["data_samples"]
                if "contribution_score" in info:
                    metrics["contribution_score"] = info["contribution_score"]
                if "availability" in info:
                    metrics["availability"] = info["availability"]
                
                # Add metrics to dictionary
                if metrics:
                    node_metrics[node_id] = metrics
        
        # Calculate global metrics
        global_metrics = {
            "nodes_count": len(visualization["nodes"]),
            "edges_count": len(visualization["edges"]),
            "average_latency": self._calculate_average_latency(visualization["edges"]),
            "connectivity_density": len(visualization["edges"]) / max(1, len(visualization["nodes"])),
            "server_client_ratio": self._calculate_server_client_ratio(visualization["nodes"])
        }
        
        # Add metrics to visualization
        visualization["metrics"] = {
            "global": global_metrics,
            "nodes": node_metrics
        }
        
        return visualization
    
    def _calculate_average_latency(self, edges: List[Dict[str, Any]]) -> float:
        """
        Calculate average latency from edges.
        
        Args:
            edges: List of edges
            
        Returns:
            Average latency
        """
        if not edges:
            return 0.0
        
        total_latency = sum(edge.get("latency", 0) for edge in edges)
        return total_latency / len(edges)
    
    def _calculate_server_client_ratio(self, nodes: List[Dict[str, Any]]) -> float:
        """
        Calculate server to client ratio.
        
        Args:
            nodes: List of nodes
            
        Returns:
            Server to client ratio
        """
        servers = sum(1 for node in nodes if node.get("type") == "server")
        clients = sum(1 for node in nodes if node.get("type") != "server")
        
        if clients == 0:
            return float('inf')
        
        return servers / clients
    
    def create_html_visualization(self, topology_data: Dict[str, Any], output_file: str = "network_topology.html") -> str:
        """
        Create HTML visualization of network topology.
        
        Args:
            topology_data: Network topology data
            output_file: Name of output HTML file
            
        Returns:
            Path to the generated HTML file
        """
        # Generate JSON visualization data
        json_path = self.generate_visualization(topology_data)
        
        # Create HTML template with embedded visualization
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Federated Learning Network Topology</title>
            <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <style type="text/css">
                #network-container {
                    width: 100%;
                    height: 600px;
                    border: 1px solid #ddd;
                    background-color: #f5f5f5;
                }
                .metrics-panel {
                    padding: 10px;
                    background-color: #fff;
                    border: 1px solid #ddd;
                    margin-top: 10px;
                }
                .node-details {
                    display: none;
                    margin-top: 10px;
                    padding: 10px;
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                }
            </style>
        </head>
        <body>
            <h1>Federated Learning Network Topology</h1>
            <div id="network-container"></div>
            <div class="metrics-panel">
                <h2>Network Metrics</h2>
                <div id="global-metrics"></div>
            </div>
            <div class="node-details" id="node-details">
                <h2>Node Details</h2>
                <div id="selected-node-info"></div>
            </div>
            
            <script type="text/javascript">
                // Fetch visualization data
                fetch('DATA_URL')
                    .then(response => response.json())
                    .then(data => {
                        const nodes = new vis.DataSet(data.nodes);
                        const edges = new vis.DataSet(data.edges);
                        
                        // Create network
                        const container = document.getElementById('network-container');
                        const networkData = {
                            nodes: nodes,
                            edges: edges
                        };
                        const options = {
                            nodes: {
                                shape: 'circle',
                                font: {
                                    size: 14
                                }
                            },
                            edges: {
                                smooth: {
                                    type: 'continuous'
                                },
                                font: {
                                    size: 12,
                                    align: 'middle'
                                }
                            },
                            physics: {
                                stabilization: true,
                                barnesHut: {
                                    gravitationalConstant: -2000,
                                    centralGravity: 0.3,
                                    springLength: 200
                                }
                            },
                            interaction: {
                                tooltipDelay: 200,
                                hideEdgesOnDrag: true
                            }
                        };
                        
                        const network = new vis.Network(container, networkData, options);
                        
                        // Display global metrics
                        if (data.metrics && data.metrics.global) {
                            const metricsDiv = document.getElementById('global-metrics');
                            const metrics = data.metrics.global;
                            
                            let metricsHtml = '<ul>';
                            metricsHtml += `<li>Nodes: ${metrics.nodes_count}</li>`;
                            metricsHtml += `<li>Edges: ${metrics.edges_count}</li>`;
                            metricsHtml += `<li>Average Latency: ${metrics.average_latency.toFixed(2)} ms</li>`;
                            metricsHtml += `<li>Connectivity Density: ${metrics.connectivity_density.toFixed(2)}</li>`;
                            metricsHtml += `<li>Server/Client Ratio: ${metrics.server_client_ratio.toFixed(3)}</li>`;
                            metricsHtml += '</ul>';
                            
                            metricsDiv.innerHTML = metricsHtml;
                        }
                        
                        // Handle node selection
                        network.on("click", function (params) {
                            if (params.nodes.length > 0) {
                                const nodeId = params.nodes[0];
                                const node = nodes.get(nodeId);
                                const nodeMetrics = data.metrics?.nodes?.[nodeId] || {};
                                
                                // Show node details panel
                                const detailsDiv = document.getElementById('node-details');
                                detailsDiv.style.display = 'block';
                                
                                // Populate node details
                                const infoDiv = document.getElementById('selected-node-info');
                                let infoHtml = `<h3>${node.label} (${node.type})</h3>`;
                                
                                // Add node info
                                if (node.info) {
                                    infoHtml += '<h4>Information</h4><ul>';
                                    for (const [key, value] of Object.entries(node.info)) {
                                        if (typeof value !== 'object') {
                                            infoHtml += `<li>${key}: ${value}</li>`;
                                        }
                                    }
                                    infoHtml += '</ul>';
                                }
                                
                                // Add node metrics
                                if (Object.keys(nodeMetrics).length > 0) {
                                    infoHtml += '<h4>Metrics</h4><ul>';
                                    for (const [key, value] of Object.entries(nodeMetrics)) {
                                        infoHtml += `<li>${key}: ${value}</li>`;
                                    }
                                    infoHtml += '</ul>';
                                }
                                
                                infoDiv.innerHTML = infoHtml;
                            }
                        });
                    })
                    .catch(error => console.error('Error loading visualization data:', error));
            </script>
        </body>
        </html>
        """.replace('DATA_URL', os.path.basename(json_path))
        
        # Write HTML file
        html_path = os.path.join(self.output_dir, output_file)
        with open(html_path, "w") as f:
            f.write(html_template)
        
        logger.info("HTML network visualization created at %s", html_path)
        return html_path 