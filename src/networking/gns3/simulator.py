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

import logging
import requests
import json
import os
from typing import Tuple, Optional, Dict, Any, List

class GNS3Simulator:
    def __init__(self, host: str = "localhost", port: int = 3080):
        """Initialize GNS3 simulator.
        
        Args:
            host (str): GNS3 server host
            port (int): GNS3 server port
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/v2"
        self.api = requests.Session()
        self._logger = logging.getLogger(__name__)
        self.templates = {}
        
    def create_template(self, template_config: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Create a new template in GNS3.
        
        Args:
            template_config (dict): Template configuration dictionary
            
        Returns:
            tuple: (success, template) where success is a boolean indicating if the operation succeeded,
                  and template is the created template object or None if failed
        """
        try:
            response = self.api.post(f"{self.base_url}/templates", json=template_config)
            if response.status_code == 201:  # Created
                template = response.json()
                self._logger.info(f"Template created successfully: {template['name']}")
                return True, template
            else:
                self._logger.error(f"Failed to create template. Status: {response.status_code}, Response: {response.text}")
                return False, None
        except Exception as e:
            self._logger.error(f"Error creating template: {str(e)}")
            return False, None
            
    def load_templates_from_config(self, config_dir: str) -> bool:
        """Load templates from configuration directory.
        
        Args:
            config_dir (str): Path to the configuration directory
            
        Returns:
            bool: True if all templates were loaded successfully, False otherwise
        """
        try:
            templates_dir = os.path.join(config_dir, "gns3", "templates")
            if not os.path.exists(templates_dir):
                self._logger.error(f"Templates directory not found: {templates_dir}")
                return False
                
            template_files = [
                "fl_server.json",
                "fl_client.json",
                "policy_engine.json",
                "sdn_controller.json"
            ]
            
            for template_file in template_files:
                template_path = os.path.join(templates_dir, template_file)
                if not os.path.exists(template_path):
                    self._logger.error(f"Template file not found: {template_path}")
                    continue
                    
                with open(template_path, 'r') as f:
                    template_config = json.load(f)
                    
                success, template = self.create_template(template_config)
                if success and template:
                    self.templates[template['name']] = template
                    self._logger.info(f"Loaded template: {template['name']}")
                else:
                    self._logger.error(f"Failed to load template from {template_file}")
                    return False
                    
            return True
            
        except Exception as e:
            self._logger.error(f"Error loading templates: {str(e)}")
            return False
            
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by its name.
        
        Args:
            name (str): Name of the template
            
        Returns:
            Optional[Dict[str, Any]]: Template configuration if found, None otherwise
        """
        return self.templates.get(name)
        
    def deploy_component(self, project_id: str, template_name: str, node_name: str, 
                        x: int = 0, y: int = 0) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Deploy a component using a template.
        
        Args:
            project_id (str): ID of the GNS3 project
            template_name (str): Name of the template to use
            node_name (str): Name for the new node
            x (int): X coordinate for node placement
            y (int): Y coordinate for node placement
            
        Returns:
            tuple: (success, node) where success is a boolean indicating if the operation succeeded,
                  and node is the created node object or None if failed
        """
        try:
            template = self.get_template_by_name(template_name)
            if not template:
                self._logger.error(f"Template not found: {template_name}")
                return False, None
                
            node_data = {
                "name": node_name,
                "node_type": template["template_type"],
                "template_id": template["template_id"],
                "compute_id": template["compute_id"],
                "x": x,
                "y": y,
                "properties": template.get("properties", {})
            }
            
            response = self.api.post(f"{self.base_url}/projects/{project_id}/nodes", json=node_data)
            if response.status_code == 201:
                node = response.json()
                self._logger.info(f"Node created successfully: {node_name}")
                return True, node
            else:
                self._logger.error(f"Failed to create node. Status: {response.status_code}, Response: {response.text}")
                return False, None
                
        except Exception as e:
            self._logger.error(f"Error deploying component: {str(e)}")
            return False, None 