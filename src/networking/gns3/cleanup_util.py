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
GNS3 Cleanup Utility.

This module provides utilities for cleaning up GNS3 resources, including:
- Freeing up used ports
- Deleting unused VPCS nodes
- Cleaning up old projects
"""

import logging
import time
from typing import Dict, List, Tuple, Any, Optional
import requests
import datetime
import json
import subprocess
import os
import platform
import sys
import re
import traceback

logger = logging.getLogger(__name__)

class GNS3CleanupUtil:
    """Utility for cleaning up GNS3 resources."""
    
    def __init__(self, server_url: str = "http://localhost:3080", username: str = None, password: str = None, auth: Optional[Tuple[str, str]] = None):
        """
        Initialize the GNS3 cleanup utility.
        
        Args:
            server_url: URL of the GNS3 server
            username: Username for GNS3 authentication (if enabled)
            password: Password for GNS3 authentication (if enabled)
            auth: Optional tuple containing (username, password) for basic auth
        """
        self.server_url = server_url.rstrip("/")
        self.api_version = "v2"
        self.base_url = f"{self.server_url}/{self.api_version}"
        self.auth = None
        
        # Configure authentication if provided directly as auth tuple
        if auth:
            self.auth = auth
            logger.info(f"Initialized GNS3CleanupUtil with provided authentication tuple")
        # Configure authentication from username and password
        elif username and password:
            self.auth = (username, password)
            logger.info(f"Initialized GNS3CleanupUtil with authentication for user: {username}")
        else:
            logger.info(f"Initialized GNS3CleanupUtil without authentication")
        
        logger.info(f"Initialized GNS3CleanupUtil with server URL: {server_url}")
    
    def connect(self) -> bool:
        """
        Test connection to the GNS3 server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/version", timeout=5, auth=self.auth)
            if response.status_code == 200:
                logger.info(f"Connected to GNS3 server (version: {response.json().get('version')})")
                return True
            elif response.status_code in [401, 403]:
                logger.error(f"Authentication/authorization error: {response.status_code}")
                logger.error("Please check your GNS3 username and password")
                return False
            else:
                logger.error(f"Failed to connect to GNS3 server: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to GNS3 server: {e}")
            return False
    
    def get_projects(self) -> Tuple[bool, List[Dict]]:
        """
        Get all projects.
        
        Returns:
            Tuple of (success, list of projects)
        """
        try:
            response = requests.get(f"{self.base_url}/projects", timeout=10, auth=self.auth)
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to get projects: {response.status_code} - {response.text}")
                return False, []
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return False, []
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.delete(f"{self.base_url}/projects/{project_id}", timeout=10, auth=self.auth)
            if response.status_code in [200, 201, 204]:
                logger.info(f"Successfully deleted project {project_id}")
                return True
            else:
                logger.error(f"Failed to delete project {project_id}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            return False
    
    def get_nodes(self, project_id: str) -> Tuple[bool, List[Dict]]:
        """
        Get all nodes in a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Tuple of (success, list of nodes)
        """
        try:
            response = requests.get(f"{self.base_url}/projects/{project_id}/nodes", timeout=10, auth=self.auth)
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to get nodes: {response.status_code} - {response.text}")
                return False, []
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return False, []
    
    def get_node(self, project_id: str, node_id: str) -> Tuple[bool, Dict]:
        """
        Get information about a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            Tuple of (success, node_info)
        """
        try:
            response = requests.get(f"{self.base_url}/projects/{project_id}/nodes/{node_id}", timeout=10, auth=self.auth)
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to get node info: {response.status_code}")
                return False, {}
        except Exception as e:
            logger.error(f"Error getting node info: {e}")
            return False, {}
    
    def delete_node(self, project_id: str, node_id: str) -> bool:
        """
        Delete a node from a project with enhanced error handling and retries.
        
        Args:
            project_id: ID of the project containing the node
            node_id: ID of the node to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        logger.info(f"Attempting to delete node {node_id} from project {project_id}")
        
        # First check if node is running and stop it
        success, node_info = self.get_node(project_id, node_id)
        if not success:
            logger.error(f"Failed to get node info: {node_id}")
            return False
            
        if success and node_info and node_info.get('status') == 'started':
            logger.info(f"Node {node_id} is running, stopping it first...")
            if not self.stop_node(project_id, node_id):
                logger.warning(f"Failed to stop node {node_id}, will try to delete anyway")
            else:
                # Give it a moment to fully stop
                time.sleep(1)
        
        # Try to delete with limited retries
        max_retries = 2  # Reduced from 3 to avoid excessive loops
        restart_attempted = False
        
        for attempt in range(max_retries):
            try:
                # First try direct deletion
                delete_url = f"{self.server_url}/v2/projects/{project_id}/nodes/{node_id}"
                response = requests.delete(delete_url, timeout=5, auth=self.auth)
                
                if response.status_code in [200, 201, 204]:
                    logger.info(f"Successfully deleted node {node_id}")
                    return True
                elif response.status_code == 404:
                    logger.info(f"Node {node_id} already deleted or doesn't exist")
                    return True
                elif response.status_code == 403 and not restart_attempted:
                    logger.warning(f"Node deletion forbidden (403). Attempting to close project first...")
                    
                    # Only try project restart once
                    restart_attempted = True
                    if self.restart_project(project_id):
                        logger.info("Project restarted successfully, retrying deletion...")
                        time.sleep(2)  # Wait for project to fully restart
                    else:
                        logger.error("Failed to restart project, deletion might fail")
                        # Instead of completely failing, try direct deletion once more
                        
                    # Check if node still exists after restart
                    check_success, _ = self.get_node(project_id, node_id)
                    if not check_success:
                        logger.info(f"Node {node_id} no longer exists after project restart")
                        return True
                else:
                    error_msg = f"Failed to delete node: HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg += f" - {error_data['message']}"
                    except:
                        pass
                    
                    logger.error(error_msg)
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying deletion (attempt {attempt+2}/{max_retries})")
                        time.sleep(2)  # Wait before retry
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"Error during deletion request: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retry
        
        logger.error(f"Failed to delete node {node_id} after {max_retries} attempts")
        return False
    
    def stop_node(self, project_id: str, node_id: str) -> bool:
        """
        Stop a node.
        
        Args:
            project_id: ID of the project
            node_id: ID of the node
            
        Returns:
            True if successful
        """
        try:
            url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}/stop"
            response = requests.post(url, timeout=5, auth=self.auth)
            if response.status_code in [200, 201, 204]:
                return True
            else:
                logger.error(f"Failed to stop node: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error stopping node: {e}")
            return False
    
    def get_computes(self) -> Tuple[bool, List[Dict]]:
        """
        Get all compute nodes.
        
        Returns:
            Tuple of (success, list of compute nodes)
        """
        try:
            response = requests.get(f"{self.base_url}/computes", timeout=10)
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Failed to get compute nodes: {response.status_code} - {response.text}")
                return False, []
        except Exception as e:
            logger.error(f"Error getting compute nodes: {e}")
            return False, []
    
    def check_vpcs_limit(self) -> Dict[str, int]:
        """
        Check the limit of VPCS VMs that can be created.
        
        Returns:
            Dictionary with total_vpcs, limit, and available
        """
        try:
            # Get VPCS VM limit info
            vpcs_total = 0
            
            # Count VPCS nodes across all projects
            success, projects = self.get_projects()
            if not success:
                return {"total_vpcs": 0, "limit": 100, "available": 100}
            
            for project in projects:
                project_id = project.get('project_id')
                success, nodes = self.get_nodes(project_id)
                if success:
                    for node in nodes:
                        if node.get('node_type') == 'vpcs':
                            vpcs_total += 1
            
            # Default limit is usually around 100 (but can vary by system)
            vpcs_limit = 100
            vpcs_available = max(0, vpcs_limit - vpcs_total)
            
            return {
                "total_vpcs": vpcs_total,
                "limit": vpcs_limit,
                "available": vpcs_available
            }
        except Exception as e:
            logger.error(f"Error checking VPCS limit: {e}")
            return {"total_vpcs": 0, "limit": 100, "available": 100}
            
    def cleanup_unused_vpcs(self) -> int:
        """
        Clean up unused VPCS VMs.
        
        Returns:
            Number of VPCS VMs deleted
        """
        try:
            deleted_count = 0
            skipped_count = 0
            
            # Get all projects
            success, projects = self.get_projects()
            if not success:
                return 0
            
            # Find all VPCS nodes in each project
            for project in projects:
                project_id = project.get('project_id')
                project_name = project.get('name', 'Unknown')
                project_status = project.get('status', '')
                
                # If the project is locked or protected, restart it first
                if project_status == 'opened':
                    logger.info(f"Project {project_name} is open. Attempting to restart it first.")
                    self.restart_project(project_id, project_name)
                
                success, nodes = self.get_nodes(project_id)
                if not success:
                    logger.warning(f"Failed to get nodes for project {project_name}")
                    continue
                
                # Delete VPCS nodes that are not running
                vpcs_nodes = [node for node in nodes if node.get('node_type') == 'vpcs' 
                              and node.get('status') != 'started']
                
                if not vpcs_nodes:
                    logger.debug(f"No unused VPCS nodes found in project {project_name}")
                    continue
                
                logger.info(f"Found {len(vpcs_nodes)} unused VPCS nodes in project {project_name}")
                
                # First, try to close the project to unlock it
                project_unlocked = False
                if project_status == 'opened' and vpcs_nodes:
                    try:
                        logger.info(f"Closing project {project_name} before deleting nodes")
                        close_url = f"{self.base_url}/projects/{project_id}/close"
                        close_response = requests.post(close_url, timeout=5)
                        if close_response.status_code in [200, 201, 204]:
                            logger.info(f"Successfully closed project {project_name}")
                            project_unlocked = True
                            time.sleep(1)  # Brief pause
                        else:
                            logger.warning(f"Failed to close project {project_name}: {close_response.status_code}")
                    except Exception as e:
                        logger.warning(f"Error closing project {project_name}: {e}")
                
                for node in vpcs_nodes:
                    node_id = node.get('node_id')
                    node_name = node.get('name', 'Unknown')
                    
                    logger.info(f"Deleting unused VPCS node {node_name} in project {project_name}")
                    
                    # First try normal deletion
                    if self.delete_node(project_id, node_id):
                        deleted_count += 1
                        continue
                    
                    # If the normal deletion failed, try more aggressive methods
                    logger.warning(f"Normal deletion failed for node {node_name}. Trying more aggressive approach.")
                    
                    try:
                        # Try with direct API call with better error handling
                        delete_url = f"{self.base_url}/projects/{project_id}/nodes/{node_id}"
                        delete_response = requests.delete(delete_url, timeout=10)
                        
                        if delete_response.status_code in [200, 201, 204]:
                            logger.info(f"Successfully deleted node {node_name} with direct API call")
                            deleted_count += 1
                        elif delete_response.status_code == 403:
                            # Try restarting the project completely
                            logger.warning(f"Node {node_name} is locked (403). Attempting to restart project...")
                            if self.restart_project(project_id):
                                # Try deletion again after restart
                                delete_response = requests.delete(delete_url, timeout=10)
                                if delete_response.status_code in [200, 201, 204]:
                                    logger.info(f"Successfully deleted node {node_name} after project restart")
                                    deleted_count += 1
                                else:
                                    logger.error(f"Failed to delete node {node_name} even after project restart: {delete_response.status_code}")
                            else:
                                logger.error(f"Failed to restart project {project_name}")
                                skipped_count += 1
                        else:
                            logger.error(f"Failed to delete node {node_name}: {delete_response.status_code}")
                            skipped_count += 1
                    except Exception as e:
                        logger.error(f"Error during aggressive deletion of node {node_name}: {e}")
                        skipped_count += 1
            
            logger.info(f"Cleanup complete: {deleted_count} nodes deleted, {skipped_count} nodes skipped")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up unused VPCS VMs: {e}")
            return 0
    
    def cleanup_unused_vpcs_nodes(self, max_cleanup_time=120) -> int:
        """
        Find and delete unused VPCS nodes across all projects.
        
        Args:
            max_cleanup_time: Maximum time in seconds to spend on cleanup to avoid excessive looping
        
        Returns:
            Number of nodes deleted
        """
        start_time = time.time()
        logger.info(f"Cleaning up unused VPCS nodes with time limit of {max_cleanup_time}s")
        nodes_stopped = 0
        nodes_deleted = 0
        deletion_attempts = 0
        already_attempted = set()  # Track nodes we've already tried to delete
        max_nodes_per_project = 5  # Reduced from 10 to 5 to minimize time spent per project
        max_projects = 3  # Reduced from 5 to 3 to focus on fewer projects more effectively
        max_time_per_project = min(max_cleanup_time * 0.4, 45)  # Max 45s per project or 40% of total time
        
        try:
            # Get all projects
            success, projects = self.get_projects()
            if not success:
                logger.error("Failed to get projects for cleanup")
                return 0
                
            # Limit number of projects to process
            projects_to_process = projects[:max_projects]
            logger.info(f"Processing {len(projects_to_process)} of {len(projects)} projects")
            
            # Process projects 
            for project_idx, project in enumerate(projects_to_process):
                # Check if we've spent too much time
                elapsed_time = time.time() - start_time
                if elapsed_time > max_cleanup_time:
                    logger.warning(f"Cleanup time limit ({max_cleanup_time}s) exceeded after {elapsed_time:.1f}s, stopping further cleanup")
                    break
                    
                project_id = project.get('project_id')
                project_name = project.get('name', '')
                project_start_time = time.time()
                
                logger.info(f"Checking project {project_name} for unused VPCS nodes")
                
                # Get all nodes in the project
                success, nodes = self.get_nodes(project_id)
                if not success:
                    logger.warning(f"Failed to get nodes for project {project_name}")
                    continue
                
                # Find VPCS nodes - prioritize stopped nodes for cleanup
                vpcs_nodes = [node for node in nodes if node.get('node_type') == 'vpcs']
                stopped_nodes = [node for node in vpcs_nodes if node.get('status', '') != 'started']
                started_nodes = [node for node in vpcs_nodes if node.get('status', '') == 'started']
                
                logger.info(f"Found {len(vpcs_nodes)} VPCS nodes in project {project_name} ({len(stopped_nodes)} stopped, {len(started_nodes)} running)")
                
                if vpcs_nodes:
                    # Try to unlock the project once before processing nodes
                    if len(vpcs_nodes) > 1:
                        project_unlock_attempted = self.restart_project(project_id, project_name)
                        if not project_unlock_attempted:
                            logger.warning(f"Failed to unlock project {project_name}, will try individual nodes anyway")
                        
                        # Small delay after project restart whether successful or not
                        time.sleep(1)
                    
                    # Prioritize stopped nodes, but include some running nodes if needed
                    nodes_to_process = stopped_nodes.copy()
                    
                    # Add running nodes to process if we don't have enough stopped nodes
                    if len(nodes_to_process) < max_nodes_per_project and started_nodes:
                        # Only process a few running nodes
                        nodes_to_process.extend(started_nodes[:max(1, max_nodes_per_project - len(nodes_to_process))])
                    
                    # Limit total nodes to process
                    nodes_to_process = nodes_to_process[:max_nodes_per_project]
                    logger.info(f"Processing {len(nodes_to_process)} of {len(vpcs_nodes)} VPCS nodes in project {project_name}")
                    
                    # Process nodes with project time limit
                    for node_idx, node in enumerate(nodes_to_process):
                        # Check if we've spent too much time on this project
                        project_elapsed = time.time() - project_start_time
                        if project_elapsed > max_time_per_project:
                            logger.warning(f"Project time limit exceeded after {project_elapsed:.1f}s, moving to next project")
                            break
                            
                        # Check overall timeout
                        total_elapsed = time.time() - start_time
                        if total_elapsed > max_cleanup_time:
                            logger.warning(f"Cleanup time limit ({max_cleanup_time}s) exceeded after {total_elapsed:.1f}s, stopping cleanup")
                            return nodes_stopped + nodes_deleted
                            
                        node_id = node.get('node_id')
                        node_name = node.get('name', '')
                        node_status = node.get('status', '')
                        
                        # Skip already attempted nodes
                        node_key = f"{project_id}:{node_id}"
                        if node_key in already_attempted:
                            logger.debug(f"Skipping already attempted node {node_name}")
                            continue
                            
                        # Record attempt
                        already_attempted.add(node_key)
                        deletion_attempts += 1
                        
                        node_start_time = time.time()
                        logger.info(f"Processing VPCS node {node_name} (status: {node_status}) in project {project_name} ({node_idx+1}/{len(nodes_to_process)})")
                        
                        # Set a maximum time per node
                        max_time_per_node = min(15, max_time_per_project / max_nodes_per_project)
                        
                        # Check if node is running and stop it first
                        if node_status == 'started':
                            logger.info(f"Stopping running node {node_name}")
                            success = self.stop_node(project_id, node_id)
                            if success:
                                nodes_stopped += 1
                                logger.info(f"Stopped node {node_name}")
                                # Give it a moment to fully stop
                                time.sleep(0.5)
                            else:
                                logger.warning(f"Failed to stop node {node_name}")
                        
                        # Check if we still have time to delete the node
                        node_elapsed = time.time() - node_start_time
                        remaining_node_time = max_time_per_node - node_elapsed
                        
                        if remaining_node_time < 2:
                            logger.warning(f"Not enough time remaining for node deletion, skipping")
                            continue
                            
                        # Try to delete the node
                        logger.info(f"Deleting node {node_name}")
                        success = self.delete_node(project_id, node_id)
                        
                        node_elapsed = time.time() - node_start_time
                        if success:
                            nodes_deleted += 1
                            logger.info(f"Successfully deleted node {node_name} (took {node_elapsed:.1f}s)")
                        else:
                            logger.warning(f"Failed to delete node {node_name} (took {node_elapsed:.1f}s)")
                        
                        # Small pause between node operations to avoid overwhelming the server
                        if node_idx < len(nodes_to_process) - 1:
                            time.sleep(0.5)
                
                # Check project timeout again
                project_elapsed = time.time() - project_start_time
                logger.info(f"Completed processing project {project_name} in {project_elapsed:.1f}s")
                
                # Small pause between projects to avoid overwhelming the server
                if project_idx < len(projects_to_process) - 1:
                    time.sleep(2)
                
            total_elapsed_time = time.time() - start_time
            logger.info(f"Finished VPCS cleanup after {total_elapsed_time:.1f}s: {deletion_attempts} deletion attempts, {nodes_stopped} nodes stopped, {nodes_deleted} nodes deleted")
            return nodes_stopped + nodes_deleted
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error cleaning up VPCS nodes after {elapsed_time:.1f}s: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return nodes_stopped
    
    def cleanup_old_projects(self, days_old: float = 1.0) -> int:
        """
        Delete old projects that haven't been modified recently.
        
        Args:
            days_old: Delete projects older than this many days
            
        Returns:
            Number of projects deleted
        """
        try:
            success, projects = self.get_projects()
            if not success:
                return 0
            
            # Calculate cutoff time
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=days_old)
            # Convert to ISO format string for comparison
            cutoff_str = cutoff_time.isoformat()
            
            deleted_count = 0
            for project in projects:
                project_id = project.get('project_id')
                project_name = project.get('name', 'Unknown')
                
                # Skip the project if it's the current one we're using
                if 'status' in project and project['status'] == 'opened':
                    logger.info(f"Closing active project before cleanup: {project_name}")
                    try:
                        # Try to close the project first
                        close_url = f"{self.base_url}/projects/{project_id}/close"
                        close_response = requests.post(close_url, timeout=5)
                        if close_response.status_code in [200, 201, 204]:
                            logger.info(f"Successfully closed project {project_name}")
                            time.sleep(1)  # Brief pause
                        else:
                            logger.warning(f"Failed to close project {project_name}: {close_response.status_code}")
                            continue  # Skip this project if we can't close it
                    except Exception as e:
                        logger.warning(f"Error closing project {project_name}: {e}")
                        continue  # Skip this project
                
                # Check if the project is old enough to delete
                last_modified = project.get('last_modified', '')
                if last_modified and last_modified < cutoff_str:
                    logger.info(f"Deleting old project: {project_name} (Last modified: {last_modified})")
                    
                    try:
                        # First try to delete the project directly
                        delete_response = requests.delete(f"{self.base_url}/projects/{project_id}", timeout=10)
                        
                        if delete_response.status_code in [200, 201, 204]:
                            deleted_count += 1
                            logger.info(f"Successfully deleted project {project_name}")
                        elif delete_response.status_code == 403:
                            # If deletion is forbidden (403), try to close it first
                            logger.warning(f"Project {project_name} is locked (403). Trying to close it first...")
                            close_url = f"{self.base_url}/projects/{project_id}/close"
                            close_response = requests.post(close_url, timeout=5)
                            
                            if close_response.status_code in [200, 201, 204]:
                                # Try deletion again after closing
                                time.sleep(1)  # Brief pause after closing
                                delete_response = requests.delete(f"{self.base_url}/projects/{project_id}", timeout=10)
                                
                                if delete_response.status_code in [200, 201, 204]:
                                    deleted_count += 1
                                    logger.info(f"Successfully deleted project {project_name} after closing")
                                else:
                                    logger.error(f"Failed to delete project {project_name} even after closing: {delete_response.status_code}")
                            else:
                                logger.error(f"Failed to close project {project_name}: {close_response.status_code}")
                        else:
                            logger.error(f"Failed to delete project {project_name}: {delete_response.status_code}")
                    except Exception as e:
                        logger.error(f"Error deleting project {project_name}: {e}")
                else:
                    logger.debug(f"Keeping recent project: {project_name} (Last modified: {last_modified})")
            
            logger.info(f"Deleted {deleted_count} old projects")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old projects: {e}")
            return 0
    
    def free_used_ports(self) -> int:
        """
        Free all ports that might be causing conflicts with GNS3.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # This function is OS-dependent
            if platform.system() == "Windows":
                return self._free_ports_windows()
            elif platform.system() == "Linux":
                return self._free_ports_linux()
            elif platform.system() == "Darwin":  # macOS
                return self._free_ports_macos()
            else:
                logger.error(f"Unsupported OS for port freeing: {platform.system()}")
                return 0
        except Exception as e:
            logger.error(f"Error freeing used ports: {e}")
            return ports_freed
            
    def free_gns3_nio_udp_ports(self) -> int:
        """
        Free UDP ports specifically used by GNS3 NIOs (Network I/O).
        GNS3 uses UDP ports in the 10000-20000 range for NIOs between devices.
        
        Returns:
            int: Number of ports freed
        """
        try:
            logger.info("Freeing UDP ports used by GNS3 NIOs...")
            if platform.system() == "Windows":
                return self._free_nio_udp_ports_windows()
            elif platform.system() == "Linux":
                return self._free_nio_udp_ports_linux()
            elif platform.system() == "Darwin":  # macOS
                return self._free_nio_udp_ports_macos()
            else:
                logger.error(f"Unsupported OS for NIO UDP port freeing: {platform.system()}")
                return 0
        except Exception as e:
            logger.error(f"Error freeing GNS3 NIO UDP ports: {e}")
            return 0
            
    def _free_nio_udp_ports_windows(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on Windows.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Check if we have admin privileges first
            has_admin = False
            try:
                subprocess.check_output("net session >nul 2>&1", shell=True)
                has_admin = True
                logger.info("Running with admin privileges, can terminate system processes")
            except:
                logger.warning("Not running with admin privileges, some processes cannot be killed")
            
            # Get all UDP ports with PIDs
            try:
                # Use netstat to get UDP listening ports
                netstat_output = subprocess.check_output("netstat -ano -p UDP", shell=True).decode('utf-8')
                
                # Parse the output to find UDP ports in the 10000-20000 range with PIDs
                import re
                udp_port_regex = re.compile(r':(\d{5})\s+.*?(\d+)')
                matches = udp_port_regex.findall(netstat_output)
                
                # Filter to only include ports in GNS3's NIO range (10000-20000)
                gns3_nio_matches = [(port, pid) for port, pid in matches if 10000 <= int(port) <= 20000]
                
                logger.info(f"Found {len(gns3_nio_matches)} UDP ports in GNS3 NIO range (10000-20000)")
                
                # Track terminated processes to avoid duplicates
                terminated_pids = set()
                
                for port, pid in gns3_nio_matches:
                    try:
                        pid_num = int(pid)
                        
                        # Skip if already terminated
                        if pid_num in terminated_pids:
                            continue
                            
                        # Skip system processes with low PIDs if we don't have admin rights
                        if pid_num < 1000 and not has_admin:
                            logger.info(f"Skipping system process {pid} using UDP port {port} (requires admin)")
                            continue
                        
                        # Get process info
                        try:
                            task_info = subprocess.check_output(f"tasklist /FI \"PID eq {pid}\"", shell=True).decode('utf-8')
                            is_system_critical = "System" in task_info or "svchost.exe" in task_info
                            
                            # Handle system-critical processes
                            if is_system_critical:
                                if has_admin:
                                    logger.warning(f"Found system process {pid} ({task_info.split()[0]}) using UDP port {port}")
                                else:
                                    logger.warning(f"Skipping system process {pid} using UDP port {port}")
                                    continue
                        except:
                            logger.warning(f"Could not determine process type for PID {pid}")
                        
                        # Terminate the process
                        logger.info(f"Attempting to free UDP port {port} used by PID {pid}")
                        
                        # Skip actual GNS3 processes - we don't want to kill GNS3 itself
                        if "gns3" in task_info.lower() or "dynamips" in task_info.lower() or "vpcs" in task_info.lower():
                            logger.info(f"Skipping GNS3-related process {pid}")
                            continue
                            
                        result = subprocess.call(f"taskkill /PID {pid}", shell=True)
                        if result != 0:
                            if has_admin:
                                logger.info(f"Using force to terminate process {pid}")
                                result = subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                                if result == 0:
                                    ports_freed += 1
                                    terminated_pids.add(pid_num)
                                    logger.info(f"Successfully terminated process {pid} with force")
                                else:
                                    logger.warning(f"Could not terminate process {pid} even with force")
                            else:
                                logger.warning(f"Could not terminate process {pid}, admin rights required")
                        else:
                            ports_freed += 1
                            terminated_pids.add(pid_num)
                            logger.info(f"Successfully terminated process {pid} gracefully")
                    except Exception as e:
                        logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
                
                logger.info(f"Freed {ports_freed} UDP ports on Windows")
                
                # As a last resort, try to reset the TCP/IP stack if no ports were freed and we have admin
                if ports_freed == 0 and has_admin:
                    try:
                        logger.warning("No UDP ports freed, attempting to reset Windows TCP/IP stack")
                        subprocess.call("netsh winsock reset", shell=True)
                        logger.info("Windows TCP/IP stack reset, a system restart is recommended")
                    except Exception as reset_error:
                        logger.error(f"Failed to reset TCP/IP stack: {reset_error}")
                
                return ports_freed
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to run netstat command: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on Windows: {e}")
            return 0
            
    def _free_nio_udp_ports_linux(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on Linux.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Get all UDP ports with PIDs
            try:
                # Try ss command first (more modern)
                netstat_cmd = "ss -lunp 2>/dev/null"
                netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Fallback to netstat if ss is not available
                    netstat_cmd = "netstat -lunp 2>/dev/null"
                    netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
                except subprocess.CalledProcessError:
                    logger.error("Failed to run netstat/ss command")
                    return 0
            
            # Parse the output to find UDP ports in the 10000-20000 range with PIDs
            import re
            
            # Handle both ss and netstat formats
            udp_port_regex = re.compile(r':(\d{5})\s+.*?(?:users:\(\(".*?",pid=(\d+).*?\)|(\d+)/.*?)(?:\)|\s)')
            matches = udp_port_regex.findall(netstat_output)
            
            # Process matches - extract port and pid
            nio_ports = []
            for match in matches:
                port = match[0]
                # Handle different formats (ss vs netstat)
                pid = match[1] if match[1] else match[2]
                if pid and 10000 <= int(port) <= 20000:
                    nio_ports.append((port, pid))
            
            logger.info(f"Found {len(nio_ports)} UDP ports in GNS3 NIO range (10000-20000)")
            
            # Track terminated processes to avoid duplicates
            terminated_pids = set()
            
            for port, pid in nio_ports:
                try:
                    pid_num = int(pid)
                    
                    # Skip if already terminated
                    if pid_num in terminated_pids:
                        continue
                    
                    # Get process info
                    try:
                        ps_output = subprocess.check_output(f"ps -p {pid} -o comm=", shell=True).decode('utf-8').strip()
                        is_system_critical = ps_output in ["systemd", "init", "udevd"]
                        
                        if is_system_critical:
                            logger.warning(f"Skipping system process {pid} ({ps_output}) using UDP port {port}")
                            continue
                            
                        # Skip GNS3-related processes
                        if "gns3" in ps_output.lower() or "dynamips" in ps_output.lower() or "vpcs" in ps_output.lower():
                            logger.info(f"Skipping GNS3-related process {pid} ({ps_output})")
                            continue
                    except:
                        logger.warning(f"Could not determine process type for PID {pid}")
                    
                    # Terminate the process
                    logger.info(f"Attempting to free UDP port {port} used by PID {pid}")
                    
                    # Try graceful termination first
                    try:
                        subprocess.call(f"kill {pid}", shell=True)
                        time.sleep(0.5)  # Give it a moment to terminate
                        
                        # Check if process is still running
                        try:
                            subprocess.check_output(f"ps -p {pid}", shell=True)
                            # Process still exists, try SIGKILL
                            logger.info(f"Using SIGKILL for process {pid}")
                            subprocess.call(f"kill -9 {pid}", shell=True)
                        except subprocess.CalledProcessError:
                            # Process already terminated
                            pass
                            
                        # Assume success if we get here
                        ports_freed += 1
                        terminated_pids.add(pid_num)
                        logger.info(f"Successfully terminated process {pid}")
                    except Exception as kill_error:
                        logger.error(f"Error terminating process {pid}: {kill_error}")
                        
                except Exception as e:
                    logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
            
            logger.info(f"Freed {ports_freed} UDP ports on Linux")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on Linux: {e}")
            return 0
            
    def _free_nio_udp_ports_macos(self) -> int:
        """
        Free UDP ports used by GNS3 NIOs on macOS.
        
        Returns:
            int: Number of ports freed
        """
        ports_freed = 0
        try:
            # Get all UDP ports with PIDs
            try:
                netstat_cmd = "lsof -i UDP -P -n"
                netstat_output = subprocess.check_output(netstat_cmd, shell=True).decode('utf-8')
            except subprocess.CalledProcessError:
                logger.error("Failed to run lsof command")
                return 0
            
            # Parse the output to find UDP ports in the 10000-20000 range with PIDs
            import re
            lines = netstat_output.split('\n')
            nio_ports = []
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 9:
                    match = re.search(r':(\d{5})(?:\s|$)', parts[8])
                    if match:
                        port = match.group(1)
                        if 10000 <= int(port) <= 20000:
                            pid = parts[1]
                            process = parts[0]
                            nio_ports.append((port, pid, process))
            
            logger.info(f"Found {len(nio_ports)} UDP ports in GNS3 NIO range (10000-20000)")
            
            # Track terminated processes to avoid duplicates
            terminated_pids = set()
            
            for port, pid, process in nio_ports:
                try:
                    pid_num = int(pid)
                    
                    # Skip if already terminated
                    if pid_num in terminated_pids:
                        continue
                    
                    # Skip system processes
                    if process in ["launchd", "kernel", "systemd"]:
                        logger.warning(f"Skipping system process {pid} ({process}) using UDP port {port}")
                        continue
                        
                    # Skip GNS3-related processes
                    if "gns3" in process.lower() or "dynamips" in process.lower() or "vpcs" in process.lower():
                        logger.info(f"Skipping GNS3-related process {pid} ({process})")
                        continue
                    
                    # Terminate the process
                    logger.info(f"Attempting to free UDP port {port} used by PID {pid} ({process})")
                    
                    # Try SIGTERM first
                    try:
                        subprocess.call(f"kill {pid}", shell=True)
                        time.sleep(0.5)  # Give it a moment to terminate
                        
                        # Check if process is still running
                        try:
                            subprocess.check_output(f"ps -p {pid}", shell=True)
                            # Process still exists, try SIGKILL
                            logger.info(f"Using SIGKILL for process {pid}")
                            subprocess.call(f"kill -9 {pid}", shell=True)
                        except subprocess.CalledProcessError:
                            # Process already terminated
                            pass
                            
                        # Assume success if we get here
                        ports_freed += 1
                        terminated_pids.add(pid_num)
                        logger.info(f"Successfully terminated process {pid}")
                    except Exception as kill_error:
                        logger.error(f"Error terminating process {pid}: {kill_error}")
                        
                except Exception as e:
                    logger.error(f"Error freeing UDP port {port} used by PID {pid}: {e}")
            
            logger.info(f"Freed {ports_freed} UDP ports on macOS")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing NIO UDP ports on macOS: {e}")
            return 0
    
    def _free_ports_windows(self, min_port=5000, max_port=10000, timeout=30) -> int:
        """
        Free ports in use on Windows systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on Windows in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            import subprocess
            import re
            
            # Run netstat to list all connections
            cmd = "netstat -ano"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error running netstat: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            ports_to_kill = []
            for line in stdout.splitlines():
                if "LISTENING" not in line:
                    continue
                    
                # Example line: TCP    0.0.0.0:5000    0.0.0.0:0    LISTENING    1234
                parts = line.split()
                if len(parts) < 5:
                    continue
                    
                # Extract port and PID
                try:
                    socket_part = parts[1]
                    for part in parts:
                        if ':' in part:
                            socket_part = part
                            break
                            
                    port_part = socket_part.split(':')[-1]
                    port = int(port_part)
                    pid = int(parts[-1])
                    
                    # Check if the port is in our range
                    if min_port <= port <= max_port:
                        ports_to_kill.append((port, pid))
                except Exception as e:
                    logger.debug(f"Error parsing netstat line '{line}': {e}")
                    continue
                    
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid in ports_to_kill:
                # Skip system PIDs (< 100) and already killed processes
                if pid < 100 or pid in killed_pids:
                    continue
                    
                try:
                    # Skip MS essential services
                    if self._is_windows_protected_process(pid):
                        logger.info(f"Skipping Windows protected process PID {pid} using port {port}")
                        continue
                    
                    # Double-check that the process is actually using the port
                    valid, command = self._get_windows_process_command(pid)
                    if not valid:
                        logger.debug(f"Process {pid} no longer exists or cannot be accessed")
                        continue
                        
                    if "system32" in command.lower() or "windows" in command.lower():
                        logger.info(f"Skipping Windows system process PID {pid} using port {port}")
                        continue
                    
                    logger.info(f"Killing process {pid} using port {port} (command: {command})")
                    kill_cmd = f"taskkill /F /PID {pid}"
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=10)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {pid} using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {pid}: {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on Windows: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_windows_protected_process(self, pid: int) -> bool:
        """
        Check if a Windows process is protected and should not be killed.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if the process is protected
        """
        # List of protected Windows services by executable name
        protected_exes = [
            "lsass.exe", "csrss.exe", "services.exe", "svchost.exe", 
            "winlogon.exe", "wininit.exe", "smss.exe", "spoolsv.exe",
            "explorer.exe", "dllhost.exe", "taskmgr.exe"
        ]
        
        try:
            import subprocess
            cmd = f"tasklist /FI \"PID eq {pid}\" /FO CSV /NH"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode != 0 or not stdout.strip():
                return False
                
            # Parse output to get executable name
            # Output format: "Image Name","PID","Session Name","Session#","Mem Usage"
            import csv
            from io import StringIO
            reader = csv.reader(StringIO(stdout))
            for row in reader:
                if row and len(row) > 1:
                    exe_name = row[0].lower()
                    for protected in protected_exes:
                        if protected.lower() in exe_name:
                            return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if process {pid} is protected: {e}")
            return False
            
    def _get_windows_process_command(self, pid: int) -> Tuple[bool, str]:
        """
        Get the command line of a Windows process.
        
        Args:
            pid: Process ID to get command for
            
        Returns:
            Tuple of (success, command)
        """
        try:
            import subprocess
            # Use wmic to get command line
            cmd = f"wmic process where processid={pid} get commandline /format:list"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=5)
            
            if process.returncode != 0:
                logger.debug(f"Error getting command for PID {pid}: {stderr}")
                return False, ""
                
            # Parse output
            command = ""
            for line in stdout.splitlines():
                if line.startswith("CommandLine="):
                    command = line[12:].strip()
                    break
                    
            return True, command
            
        except Exception as e:
            logger.debug(f"Error getting command for PID {pid}: {e}")
            return False, ""
    
    def _free_ports_linux(self, min_port=5000, max_port=10000, timeout=30) -> int:
        """
        Free ports in use on Linux systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on Linux in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            import subprocess
            import re
            
            # Check for sudo access
            has_sudo = False
            try:
                sudo_check = subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
                has_sudo = sudo_check.returncode == 0
                if has_sudo:
                    logger.info("Running with sudo privileges, can terminate system processes")
                else:
                    logger.warning("Not running with sudo privileges, some processes cannot be killed")
            except Exception as e:
                logger.warning(f"Error checking sudo privileges: {e}")
                
            # Run ss command to list all connections
            cmd = "ss -tlnp"
            if has_sudo:
                cmd = f"sudo {cmd}"
                
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error running ss command: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            # Example line: LISTEN 0 128 *:5000 *:* users:(("python",pid=1234,fd=5))
            port_regex = re.compile(r'.*:(\d+)\s+.*\("([^"]+)",pid=(\d+),')
            
            ports_to_kill = []
            for line in stdout.splitlines():
                matches = port_regex.findall(line)
                if not matches:
                    continue
                    
                for port_str, process_name, pid_str in matches:
                    try:
                        port = int(port_str)
                        pid = int(pid_str)
                        
                        # Check if the port is in our range
                        if min_port <= port <= max_port:
                            ports_to_kill.append((port, pid, process_name))
                    except Exception as e:
                        logger.debug(f"Error parsing ss line '{line}': {e}")
                        continue
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid, process_name in ports_to_kill:
                # Skip already killed processes
                if pid in killed_pids:
                    continue
                    
                try:
                    # Skip system processes if we don't have sudo
                    if not has_sudo and (pid < 1000 or self._is_linux_protected_process(process_name)):
                        logger.info(f"Skipping protected process {process_name} (PID {pid}) using port {port}")
                        continue
                    
                    # Kill the process
                    logger.info(f"Killing process {process_name} (PID {pid}) using port {port}")
                    kill_cmd = f"kill -9 {pid}"
                    if not has_sudo and pid < 1000:
                        kill_cmd = f"sudo {kill_cmd}"
                        
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=5)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {process_name} (PID {pid}) using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {process_name} (PID {pid}): {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on Linux: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_linux_protected_process(self, process_name: str) -> bool:
        """
        Check if a Linux process is protected and should not be killed.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            True if the process is protected
        """
        # List of protected Linux services by executable name
        protected_processes = [
            "systemd", "dbus", "sshd", "bash", "sh", "init", "NetworkManager",
            "rsyslogd", "dnsmasq", "crond", "chronyd", "ntpd", "udevd"
        ]
        
        for protected in protected_processes:
            if protected in process_name:
                return True
        
        return False
        
    def _free_ports_macos(self, min_port=5000, max_port=10000, timeout=30) -> int:
        """
        Free ports in use on macOS systems.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports on macOS in range {min_port}-{max_port}")
        freed_count = 0
        start_time = time.time()
        
        try:
            import subprocess
            import re
            
            # Check for admin access
            has_admin = False
            try:
                admin_check = subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
                has_admin = admin_check.returncode == 0
                if has_admin:
                    logger.info("Running with admin privileges, can terminate system processes")
                else:
                    logger.warning("Not running with admin privileges, some processes cannot be killed")
            except Exception as e:
                logger.warning(f"Error checking admin privileges: {e}")
                
            # Run lsof command to list ports in use
            cmd = "lsof -i -P -n | grep LISTEN"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0 and process.returncode != 1:  # grep returns 1 if no matches
                logger.error(f"Error running lsof command: {stderr}")
                return 0
                
            # Parse output to find ports in the given range
            # Example line: python 1234 user 5u IPv4 0xabcdef 0t0 TCP *:5000 (LISTEN)
            port_regex = re.compile(r'.*:(\d+)\s+\(LISTEN\)')
            
            ports_to_kill = []
            for line in stdout.splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue
                    
                process_name = parts[0]
                pid_str = parts[1]
                
                # Find port in the line
                matches = port_regex.findall(line)
                if not matches:
                    continue
                    
                try:
                    port = int(matches[0])
                    pid = int(pid_str)
                    
                    # Check if the port is in our range
                    if min_port <= port <= max_port:
                        ports_to_kill.append((port, pid, process_name))
                except Exception as e:
                    logger.debug(f"Error parsing lsof line '{line}': {e}")
                    continue
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            # Kill processes using those ports
            killed_pids = set()
            for port, pid, process_name in ports_to_kill:
                # Skip already killed processes
                if pid in killed_pids:
                    continue
                    
                try:
                    # Skip system processes if we don't have admin
                    if not has_admin and (pid < 1000 or self._is_macos_protected_process(process_name)):
                        logger.info(f"Skipping protected process {process_name} (PID {pid}) using port {port}")
                        continue
                    
                    # Kill the process
                    logger.info(f"Killing process {process_name} (PID {pid}) using port {port}")
                    kill_cmd = f"kill -9 {pid}"
                    if not has_admin and pid < 1000:
                        kill_cmd = f"sudo {kill_cmd}"
                        
                    kill_process = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    kill_stdout, kill_stderr = kill_process.communicate(timeout=5)
                    
                    if kill_process.returncode == 0:
                        logger.info(f"Successfully killed process {process_name} (PID {pid}) using port {port}")
                        freed_count += 1
                        killed_pids.add(pid)
                    else:
                        logger.warning(f"Failed to kill process {process_name} (PID {pid}): {kill_stderr}")
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
                
                # Check timeout again
                if time.time() - start_time > timeout:
                    logger.warning(f"Port freeing operation timed out after {timeout}s")
                    break
            
            return freed_count
            
        except Exception as e:
            logger.error(f"Error freeing ports on macOS: {e}")
            logger.error(traceback.format_exc())
            return freed_count
            
    def _is_macos_protected_process(self, process_name: str) -> bool:
        """
        Check if a macOS process is protected and should not be killed.
        
        Args:
            process_name: Name of the process to check
            
        Returns:
            True if the process is protected
        """
        # List of protected macOS services by executable name
        protected_processes = [
            "launchd", "kernel", "WindowServer", "sshd", "bash", "sh", "zsh",
            "loginwindow", "Dock", "Finder", "mds", "configd", "systemstats"
        ]
        
        for protected in protected_processes:
            if process_name.lower() == protected.lower():
                return True
        
        return False
    
    def restart_project(self, project_id: str, project_name: str = "Unknown") -> bool:
        """
        Restart a GNS3 project to unlock it for modification.
        This is helpful when nodes can't be deleted due to the project being locked.
        
        Args:
            project_id: ID of the project to restart
            project_name: Name of the project (for logging)
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Attempting to restart project {project_name} ({project_id}) to unlock it")
        
        try:
            # Step 1: Check if project exists and is accessible
            check_url = f"{self.server_url}/v2/projects/{project_id}"
            check_response = requests.get(check_url, timeout=5, auth=self.auth)
            if check_response.status_code != 200:
                logger.warning(f"Project {project_name} ({project_id}) may not exist or isn't accessible: {check_response.status_code}")
                # Don't attempt to restart a non-existent project
                return False
            
            # Get project status to determine appropriate actions
            project_status = check_response.json().get('status', '')
            logger.info(f"Project {project_name} current status: {project_status}")
            
            # If project is already closed, we can skip directly to removing locks
            if project_status != 'opened':
                logger.info(f"Project {project_name} is already closed, skipping close step")
            else:
                # Step 2: Close the project - try multiple times if needed
                max_close_attempts = 2
                for close_attempt in range(max_close_attempts):
                    logger.info(f"Closing project {project_name} (attempt {close_attempt+1}/{max_close_attempts})...")
                    close_url = f"{self.server_url}/v2/projects/{project_id}/close"
                    try:
                        # Use a longer timeout for close operations
                        close_response = requests.post(close_url, timeout=15, auth=self.auth)
                        
                        if close_response.status_code in [200, 201, 204]:
                            logger.info(f"Successfully closed project {project_name}")
                            break
                        else:
                            logger.warning(f"Failed to close project {project_name}: {close_response.status_code}")
                            if close_attempt < max_close_attempts - 1:
                                # Wait longer between retries
                                time.sleep(3)
                    except Exception as e:
                        logger.warning(f"Error during close attempt {close_attempt+1}: {e}")
                        if close_attempt < max_close_attempts - 1:
                            time.sleep(3)
                
                # Longer pause to allow project to fully close and release resources
                time.sleep(4)
            
            # Step 3: Delete any locks with retries
            max_lock_attempts = 2
            for lock_attempt in range(max_lock_attempts):
                logger.info(f"Removing locks for project {project_name} (attempt {lock_attempt+1}/{max_lock_attempts})...")
                delete_lock_url = f"{self.server_url}/v2/projects/{project_id}/lock"
                try:
                    lock_response = requests.delete(delete_lock_url, timeout=10, auth=self.auth)
                    
                    # 404 is ok - means no lock exists
                    if lock_response.status_code in [200, 201, 204, 404]:
                        logger.info(f"Successfully removed locks for project {project_name}")
                        break
                    else:
                        logger.warning(f"Failed to remove locks for project {project_name}: {lock_response.status_code}")
                        if lock_attempt < max_lock_attempts - 1:
                            time.sleep(2)
                except Exception as e:
                    logger.warning(f"Error during lock removal attempt {lock_attempt+1}: {e}")
                    if lock_attempt < max_lock_attempts - 1:
                        time.sleep(2)
            
            # Wait longer to ensure locks are fully cleared
            time.sleep(3)
            
            # Step 4: Check project status again before opening
            try:
                check_response = requests.get(check_url, timeout=5, auth=self.auth)
                if check_response.status_code == 200:
                    current_status = check_response.json().get('status', '')
                    logger.info(f"Project status before reopening: {current_status}")
                    
                    # If project is already open, we're done
                    if current_status == 'opened':
                        logger.info(f"Project {project_name} is already open, restart successful")
                        return True
                    elif current_status != 'closed':
                        logger.warning(f"Project is in intermediate state: {current_status}, waiting...")
                        time.sleep(4)  # Wait longer for transitional state to resolve
                else:
                    logger.warning(f"Failed to check project status: {check_response.status_code}")
            except Exception as e:
                logger.warning(f"Error checking project status: {e}")
            
            # Step 5: Open project with retries for handling 409 conflicts
            max_open_attempts = 3
            for open_attempt in range(max_open_attempts):
                logger.info(f"Opening project {project_name} (attempt {open_attempt+1}/{max_open_attempts})...")
                open_url = f"{self.server_url}/v2/projects/{project_id}/open"
                try:
                    # Use a longer timeout for open operations
                    open_response = requests.post(open_url, timeout=20, auth=self.auth)
                    
                    if open_response.status_code in [200, 201, 204]:
                        logger.info(f"Successfully opened project {project_name}")
                        # Wait for project to fully initialize
                        time.sleep(3)
                        return True
                    elif open_response.status_code == 409:
                        # 409 conflict needs careful handling
                        logger.warning(f"Project {project_name} has a conflict (409) - may be in transition")
                        
                        # Wait a significant time for the state to settle
                        wait_time = 5 + (open_attempt * 2)
                        logger.info(f"Waiting {wait_time}s for project state to settle...")
                        time.sleep(wait_time)
                        
                        # Check if the project is actually open despite the 409
                        try:
                            status_response = requests.get(check_url, timeout=5, auth=self.auth)
                            if status_response.status_code == 200:
                                current_status = status_response.json().get('status', '')
                                if current_status == 'opened':
                                    logger.info(f"Project {project_name} is open despite 409 error, considering restart successful")
                                    return True
                                logger.warning(f"Project status after 409: {current_status}")
                                
                                # If project is stuck in a transitioning state, try closing it again
                                if current_status in ['opening', 'closing'] and open_attempt < max_open_attempts - 1:
                                    logger.info(f"Project is in transitional state {current_status}, trying to close it again")
                                    requests.post(close_url, timeout=10, auth=self.auth)
                                    time.sleep(3)
                                    requests.delete(delete_lock_url, timeout=5, auth=self.auth)
                                    time.sleep(2)
                            else:
                                logger.warning(f"Failed to check project status after 409: {status_response.status_code}")
                        except Exception as check_e:
                            logger.warning(f"Error checking project status after 409: {check_e}")
                    else:
                        logger.warning(f"Failed to open project (attempt {open_attempt+1}): {open_response.status_code}")
                        
                        if open_attempt < max_open_attempts - 1:
                            logger.info(f"Retrying after {open_attempt+3}s wait...")
                            time.sleep(open_attempt + 3)
                except Exception as e:
                    logger.warning(f"Error during open attempt {open_attempt+1}: {e}")
                    if open_attempt < max_open_attempts - 1:
                        time.sleep(open_attempt + 3)
            
            logger.error(f"Failed to reopen project {project_name} after {max_open_attempts} attempts")
            return False
                
        except Exception as e:
            logger.error(f"Error restarting project {project_name}: {e}")
            return False

    def free_gns3_console_ports(self, min_port=5000, max_port=5999, timeout=10) -> int:
        """
        Free console ports that might be in use by GNS3.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing GNS3 console ports in range {min_port}-{max_port} with {timeout}s timeout")
        
        # Use the free_ports method with GNS3 console port range
        return self.free_ports(min_port=min_port, max_port=max_port, timeout=timeout)

    def free_ports(self, min_port=5000, max_port=10000, timeout=30) -> int:
        """
        Free ports in the specified range that might be in use.
        This is a platform-specific function that calls the appropriate implementation.
        
        Args:
            min_port: Minimum port in the range to check
            max_port: Maximum port in the range to check
            timeout: Maximum time to spend on this operation
            
        Returns:
            Number of ports freed
        """
        logger.info(f"Freeing ports in range {min_port}-{max_port} with {timeout}s timeout")
        
        # Check platform and call the appropriate method
        import platform
        system = platform.system().lower()
        
        start_time = time.time()
        ports_freed = 0
        
        try:
            if system == 'windows':
                ports_freed = self._free_ports_windows(min_port, max_port, timeout)
            elif system == 'linux':
                ports_freed = self._free_ports_linux(min_port, max_port, timeout)
            elif system == 'darwin':  # macOS
                ports_freed = self._free_ports_macos(min_port, max_port, timeout)
            else:
                logger.warning(f"Unsupported platform: {system}, cannot free ports")
                return 0
                
            elapsed = time.time() - start_time
            logger.info(f"Freed {ports_freed} ports in {elapsed:.1f}s")
            return ports_freed
            
        except Exception as e:
            logger.error(f"Error freeing ports: {e}")
            logger.error(traceback.format_exc())
            return 0

# Utility function to get a cleanup utility instance
def get_cleanup_util(server_url: str) -> GNS3CleanupUtil:
    """
    Get a GNS3 cleanup utility instance.
    
    Args:
        server_url: URL of the GNS3 server
        
    Returns:
        GNS3CleanupUtil instance
    """
    return GNS3CleanupUtil(server_url) 