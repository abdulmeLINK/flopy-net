"""
Resource management utilities for GNS3 network simulations.

This module provides functions for managing GNS3 resources like ports and VPCS capacity.
"""

import logging
import time
import traceback
import requests
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class GNS3ResourceUtils:
    """
    Utility class to handle GNS3 resource operations
    """
    
    def __init__(self, server_url: str, auth: Optional[Tuple[str, str]] = None):
        """
        Initialize the resource utils with server URL and optional authentication
        
        Args:
            server_url: The URL of the GNS3 server
            auth: Optional tuple containing (username, password) for basic auth
        """
        self.server_url = server_url
        self.auth = auth
        logger.info(f"Initialized GNS3ResourceUtils with server URL: {server_url}")
        
    def get_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all nodes for a specific project
        
        Args:
            project_id: The ID of the project to get nodes for
            
        Returns:
            List of node dictionaries
        """
        if not project_id:
            logger.warning("Cannot get nodes - project_id is not provided")
            return []
            
        try:
            url = f"{self.server_url}/v2/projects/{project_id}/nodes"
            
            response = None
            if self.auth:
                response = requests.get(url, auth=self.auth)
            else:
                response = requests.get(url)
                
            if response.status_code == 200:
                nodes = response.json()
                logger.info(f"Found {len(nodes)} nodes in project {project_id}")
                return nodes
            else:
                logger.warning(f"Failed to get nodes: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting nodes for project {project_id}: {e}")
            return []
            
    def get_links(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all links for a specific project
        
        Args:
            project_id: The ID of the project to get links for
            
        Returns:
            List of link dictionaries
        """
        if not project_id:
            logger.warning("Cannot get links - project_id is not provided")
            return []
            
        try:
            url = f"{self.server_url}/v2/projects/{project_id}/links"
            
            response = None
            if self.auth:
                response = requests.get(url, auth=self.auth)
            else:
                response = requests.get(url)
                
            if response.status_code == 200:
                links = response.json()
                logger.info(f"Found {len(links)} links in project {project_id}")
                return links
            else:
                logger.warning(f"Failed to get links: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting links for project {project_id}: {e}")
            return []

def ensure_vpcs_capacity(connector, project_id, num_nodes=10):
    logger.info(f"Ensuring VPCS capacity for {num_nodes} nodes")
    # Just a placeholder - in a real implementation, you would
    # check if the GNS3 server has the capacity to create this many VPCS nodes
    return True

def aggressive_cleanup(connector, project_id):
    logger.info(f"Performing aggressive cleanup for project {project_id}")
    try:
        # Delete all nodes in the project
        url = f"{connector.server_url}/v2/projects/{project_id}/nodes"
        response = requests.get(url, auth=connector.auth if hasattr(connector, 'auth') else None)
        
        if response.status_code == 200:
            nodes = response.json()
            logger.info(f"Found {len(nodes)} nodes to clean up")
            
            for node in nodes:
                node_id = node.get('node_id')
                if node_id:
                    delete_url = f"{connector.server_url}/v2/projects/{project_id}/nodes/{node_id}"
                    delete_response = requests.delete(delete_url, auth=connector.auth if hasattr(connector, 'auth') else None)
                    
                    if delete_response.status_code in [200, 201, 204]:
                        logger.info(f"Deleted node {node_id}")
                    else:
                        logger.warning(f"Failed to delete node {node_id}: {delete_response.status_code}")
            
            return True
        else:
            logger.warning(f"Failed to get nodes for cleanup: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error during aggressive cleanup: {e}")
        return False 