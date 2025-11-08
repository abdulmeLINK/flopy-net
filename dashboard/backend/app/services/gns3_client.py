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
Async wrapper for the GNS3API from the src directory.
This provides a clean async interface for the dashboard to interact with GNS3.
"""
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging
import os

# Import the actual GNS3 API from src
try:
    from src.networking.gns3.core.api import GNS3API
except ImportError:
    # Fallback for development environment
    import sys
    from pathlib import Path
    # Adjust path assuming this file is in app/services/
    src_path = Path(__file__).resolve().parents[3] / 'src' 
    if src_path.exists() and src_path not in sys.path:
        sys.path.insert(0, str(src_path.parent))
    from src.networking.gns3.core.api import GNS3API

# Corrected import path for config
from ..core.config import settings 

logger = logging.getLogger(__name__)

class AsyncGNS3Client:
    """Async wrapper for the GNS3API from the src directory."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the GNS3 API client.
          Args:
            base_url: URL of the GNS3 server
        """
        self.base_url = base_url or settings.GNS3_URL.rstrip('/')
        # Initialize the underlying synchronous client
        # Make sure we're using the correct API version endpoint
        self.api_version = getattr(settings, 'GNS3_API_VERSION', 'v2')
        if not self.base_url.endswith(f'/{self.api_version}'):
            self.base_url = f"{self.base_url}/{self.api_version}"
        self.client = GNS3API(self.base_url)
        logger.info(f"Initialized Async GNS3 client connected to {self.base_url} (API version: {self.api_version})")
        
        # Keep track of current project for convenience
        self.current_project_id = None
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all GNS3 projects."""
        loop = asyncio.get_event_loop()
        success, result = await loop.run_in_executor(
            None, lambda: self.client._make_request('GET', 'projects')
        )
        
        if success:
            return result
        else:
            logger.error("Failed to get GNS3 projects: %s", result.get('message', 'Unknown error'))
            # Don't return empty list, propagate the error
            raise RuntimeError(f"Failed to get GNS3 projects: {result.get('message', 'Unknown error')}")
            
    async def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a project by name."""
        projects = await self.get_projects()
        for project in projects:
            if project.get("name") == name:
                return project
        return None
    
    async def get_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all nodes in a project."""
        loop = asyncio.get_event_loop()
        success, nodes = await loop.run_in_executor(
            None, lambda: self.client._make_request('GET', f'projects/{project_id}/nodes')
        )
        
        if success:
            self.current_project_id = project_id
            return nodes
        else:
            logger.error(f"Failed to get nodes for project {project_id}")
            return []
            
    async def get_links(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all links in a project."""
        loop = asyncio.get_event_loop()
        success, links = await loop.run_in_executor(
            None, lambda: self.client._make_request('GET', f'projects/{project_id}/links')
        )
        
        if success:
            self.current_project_id = project_id
            return links
        else:
            logger.error(f"Failed to get links for project {project_id}")
            return []
            
    async def get_node(self, project_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get specific node details."""
        loop = asyncio.get_event_loop()
        success, node = await loop.run_in_executor(
            None, lambda: self.client._make_request('GET', f'projects/{project_id}/nodes/{node_id}')
        )
        
        if success:
            return node
        else:
            logger.error(f"Failed to get node {node_id} in project {project_id}")
            return None
    
    async def get_link(self, project_id: str, link_id: str) -> Optional[Dict[str, Any]]:
        """Get specific link details."""
        loop = asyncio.get_event_loop()
        success, link = await loop.run_in_executor(
            None, lambda: self.client._make_request('GET', f'projects/{project_id}/links/{link_id}')
        )
        
        if success:
            return link
        else:
            logger.error(f"Failed to get link {link_id} in project {project_id}")
            return None
    
    async def get_node_console(self, project_id: str, node_id: str) -> Dict[str, Any]:
        """Get console information for a node."""
        node = await self.get_node(project_id, node_id)
        if not node:
            return {"console_type": "none", "console_port": None}
        
        # Extract console info
        console = {
            "console_type": node.get("console_type", "none"),
            "console_port": node.get("console")
        }
        
        return console
    
    async def get_topology(self, project_id: str) -> Dict[str, Any]:
        """Get complete topology (nodes and links)."""
        nodes = await self.get_nodes(project_id)
        links = await self.get_links(project_id)
          # Build a map of node_id to node details
        node_map = {node["node_id"]: node for node in nodes}
        
        # Process links to include node information
        processed_links = []
        for link in links:
            processed_link = link.copy()
            
            # Process nodes in the link
            for endpoint in link.get("nodes", []):
                node_id = endpoint.get("node_id")
                if node_id in node_map:
                    # Add basic node info to the endpoint
                    endpoint["node_name"] = node_map[node_id].get("name", "Unknown")
                    endpoint["node_type"] = node_map[node_id].get("node_type", "Unknown")
            
            processed_links.append(processed_link)
        
        # Create the topology object
        topology = {
            "project_id": project_id,
            "nodes": nodes,
            "links": processed_links
        }
        
        return topology
    
    async def get_node_logs(self, node_id: str, project_id: Optional[str] = None) -> str:
        """
        Get logs for a specific node.
        
        Args:
            node_id: ID of the node
            project_id: ID of the project (uses current_project_id if not provided)
            
        Returns:
            String containing node logs
        """
        if not project_id:
            project_id = self.current_project_id
            
        if not project_id:
            logger.error(f"No project ID provided or stored for getting node logs")
            return "Error: No project ID available"
            
        # Call to the GNS3 API to get node logs
        loop = asyncio.get_event_loop()
        try:
            success, logs = await loop.run_in_executor(
                None, lambda: self.client._make_request('GET', f'projects/{project_id}/nodes/{node_id}/console/log')
            )
            
            if success and isinstance(logs, str):
                return logs
            elif success and isinstance(logs, dict) and 'console' in logs:
                return logs['console']
            else:
                logger.error(f"Failed to get logs for node {node_id}: {logs}")
                return f"Error retrieving logs: {logs.get('message', 'Unknown error')}" if isinstance(logs, dict) else "Error retrieving logs"
        except Exception as e:
            logger.error(f"Exception getting node logs: {str(e)}")
            return f"Error: {str(e)}"
    
    async def start_node(self, project_id: str, node_id: str) -> bool:
        """
        Start a node in GNS3.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node to start
            
        Returns:
            True if successful, False otherwise
        """
        loop = asyncio.get_event_loop()
        try:
            success, result = await loop.run_in_executor(
                None, lambda: self.client._make_request('POST', f'projects/{project_id}/nodes/{node_id}/start')
            )
            
            if success:
                logger.info(f"Successfully started node {node_id}")
                return True
            else:
                logger.error(f"Failed to start node {node_id}: {result}")
                return False
        except Exception as e:
            logger.error(f"Exception starting node: {str(e)}")
            return False
    
    async def stop_node(self, project_id: str, node_id: str) -> bool:
        """
        Stop a node in GNS3.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node to stop
            
        Returns:
            True if successful, False otherwise
        """
        loop = asyncio.get_event_loop()
        try:
            success, result = await loop.run_in_executor(
                None, lambda: self.client._make_request('POST', f'projects/{project_id}/nodes/{node_id}/stop')
            )
            
            if success:
                logger.info(f"Successfully stopped node {node_id}")
                return True
            else:
                logger.error(f"Failed to stop node {node_id}: {result}")
                return False
        except Exception as e:
            logger.error(f"Exception stopping node: {str(e)}")
            return False
    
    async def get_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available node templates.
        
        Returns:
            List of template objects
        """
        loop = asyncio.get_event_loop()
        try:
            success, templates = await loop.run_in_executor(
                None, lambda: self.client._make_request('GET', 'templates')
            )
            
            if success:
                return templates
            else:
                logger.error(f"Failed to get templates: {templates}")
                return []
        except Exception as e:
            logger.error(f"Exception getting templates: {str(e)}")
            return []
        
    async def close(self):
        """Clean up resources."""
        # The underlying GNS3API doesn't have a close method currently
        pass 