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

# Potential Refactor: This module is highly specific to GNS3 template definitions.
# Consider moving it to a more GNS3-specific location, such as:
# src/networking/gns3/template_utils.py or src/gns3/utils/template_defs.py
# to keep the top-level src/utils/ more focused on globally applicable utilities.

"""
GNS3 Template Utilities Module - Library Functions

This module provides library functions for working with GNS3 templates, specifically for registering
Docker images as templates in GNS3. It defines default template structures in code.

It is complemented by the more comprehensive CLI tool `scripts/gns3_templates.py`,
which offers more features like loading template definitions from JSON files in `config/gns3/templates/`,
user-friendly command-line arguments, and advanced template management operations.

This module might be used by programmatic parts of the system (e.g., scenario setup) for ensuring
basic templates exist, or it could be an older version of template management logic.
Consider using `scripts/gns3_templates.py` for most user-driven GNS3 template management tasks.
"""

import os
import sys
import logging
import json
import time
from typing import Dict, List, Tuple, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gns3_template_utils")

# Default FL-SDN template definitions
DEFAULT_TEMPLATES = {
    "flopynet-server": {
        "name": "flopynet-Server",
        "template_type": "docker", 
        "image": "abdulmelink/flopynet_fl_server:latest",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8",
        "category": "guest"
    },
    "flopynet-client": {
        "name": "flopynet-Client",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_fl_client:latest",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8",
        "category": "guest"
    },
    "flopynet-policy": {
        "name": "flopynet-PolicyEngine",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_policy_engine:latest",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8",
        "category": "guest"
    },
    "flopynet-sdn": {
        "name": "flopynet-SDNController",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_sdn_controller:latest",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8",
        "category": "guest"
    },
    "flopynet-collector": {
        "name": "flopynet-Collector",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_collector:latest",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8",
        "category": "guest"
    },
    # Specialized templates
    "flopynet-server-hipaa": {
        "name": "flopynet-Server-HIPAA",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_fl_server:hipaa",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nHIPAA_COMPLIANT=true",
        "category": "guest"
    },
    "flopynet-client-mri": {
        "name": "flopynet-Client-MRI",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_fl_client:mri",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nDATA_TYPE=mri",
        "category": "guest"
    },
    "flopynet-client-xray": {
        "name": "flopynet-Client-XRay",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_fl_client:xray",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nDATA_TYPE=xray",
        "category": "guest"
    },
    "flopynet-client-pathology": {
        "name": "flopynet-Client-Pathology",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_fl_client:pathology",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nDATA_TYPE=pathology",
        "category": "guest"
    },
    "flopynet-sdn-openflow": {
        "name": "flopynet-SDNController-OpenFlow",
        "template_type": "docker",
        "image": "abdulmelink/flopynet_sdn_controller:openflow",
        "adapters": 1,
        "console_type": "telnet",
        "console_auto_start": True,
        "start_command": "/bin/sh",
        "environment": "PYTHONUNBUFFERED=1\nPYTHONIOENCODING=UTF-8\nLANG=C.UTF-8\nSDN_TYPE=openflow",
        "category": "guest"
    }
}

# Health check function to verify GNS3 API is available
def check_gns3_api(api) -> bool:
    """
    Check if the GNS3 API is available and responsive.
    
    Args:
        api: GNS3 API instance
        
    Returns:
        bool: True if available, False otherwise
    """
    try:
        if hasattr(api, 'get_version'):
            success, version = api.get_version()
            if success:
                if isinstance(version, dict):
                    # If version is a dictionary, get the version attribute
                    logger.info(f"GNS3 API is available. Version: {version.get('version', 'unknown')}")
                    return True
                elif isinstance(version, str):
                    # If version is a string, return it directly
                    logger.info(f"GNS3 API is available. Version: {version}")
                    return True
        logger.error("GNS3 API is not available")
        return False
    except Exception as e:
        logger.error(f"Error checking GNS3 API: {str(e)}")
        return False

def get_templates_from_api(api) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Get all templates from the GNS3 API.
    
    Args:
        api: GNS3 API instance
        
    Returns:
        Tuple[bool, List[Dict[str, Any]]]: (success, templates list)
    """
    try:
        if hasattr(api, 'get_templates'):
            try:
                success, templates = api.get_templates()
                if success and templates is not None:
                    return True, templates
                else:
                    logger.warning(f"Failed to get templates from API: {templates}")
                    return False, []
            except Exception as e:
                logger.warning(f"Error calling get_templates: {str(e)}")
                return False, []
        else:
            logger.error("API instance does not have get_templates method")
            return False, []
    except Exception as e:
        logger.error(f"Error getting templates from API: {str(e)}")
        return False, []

def create_template(api, template_data: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Create a template in GNS3.
    
    Args:
        api: GNS3 API instance
        template_data: Template data dictionary
        
    Returns:
        Tuple[bool, Any]: (success, result)
    """
    try:
        if hasattr(api, 'create_template'):
            return api.create_template(template_data)
        else:
            logger.error("API instance does not have create_template method")
            return False, "Method not available"
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        return False, str(e)

def register_templates(api, templates: Dict[str, Dict[str, Any]], registry: str = "abdulmelink") -> Dict[str, bool]:
    """
    Register multiple templates in GNS3.
    
    Args:
        api: GNS3 API instance
        templates: Dictionary of template definitions
        registry: Docker registry to use (default: abdulmelink)
        
    Returns:
        Dict[str, bool]: Dictionary of template keys and success status
    """
    results = {}
    
    # Make sure GNS3 API is available
    if not check_gns3_api(api):
        logger.error("GNS3 API is not available")
        return {key: False for key in templates}
    
    # Remove trailing slash if present in registry
    registry = registry.rstrip('/')
    
    # Register each template
    for key, template_data in templates.items():
        template_name = template_data.get('name', key)
        logger.info(f"Registering template: {template_name}")
        
        # Check if template with same name already exists
        existing_template = get_template_by_name(api, template_name)
        if existing_template:
            logger.info(f"Template {template_name} already exists, skipping")
            results[key] = True
            continue
        
        # Copy template data to avoid modifying the original
        template_data = template_data.copy()
        
        # Make sure image has registry prefix
        if 'image' in template_data:
            # First, check if the template has a registry prefix
            image_parts = template_data['image'].split('/')
            if len(image_parts) == 1:  # No registry in image name
                template_data['image'] = f"{registry}/{image_parts[0]}"
            
            # Make sure image has the appropriate tag
            if ':' not in template_data['image']:
                template_data['image'] = f"{template_data['image']}:latest"
        
        # Create the template
        success, result = create_template(api, template_data)
        if success:
            logger.info(f"Successfully registered template: {template_name}")
            results[key] = True
        else:
            logger.error(f"Failed to register template {template_name}: {result}")
            results[key] = False
    
    # Log summary
    success_count = sum(1 for v in results.values() if v)
    logger.info(f"Registered {success_count}/{len(templates)} templates successfully")
    
    return results

def register_flopynet_templates(api, registry: str = "abdulmelink", specialized: bool = False, tag: str = "latest") -> Dict[str, bool]:
    """
    Register the default flopynet templates in GNS3.
    
    Args:
        api: GNS3 API instance
        registry: Docker registry to use (default: abdulmelink)
        specialized: Whether to include specialized templates (default: False)
        tag: Docker image tag to use (default: latest)
        
    Returns:
        Dict[str, bool]: Dictionary of template keys and success status
    """
    templates_to_register = {}
    
    # Add base templates
    for key in ["flopynet-server", "flopynet-client", "flopynet-policy", "flopynet-sdn", "flopynet-collector"]:
        if key in DEFAULT_TEMPLATES:
            template_data = DEFAULT_TEMPLATES[key].copy()
            
            # Update image tag if specified
            if tag != "latest" and "image" in template_data:
                image_parts = template_data["image"].split(":")
                if len(image_parts) > 1:
                    template_data["image"] = f"{image_parts[0]}:{tag}"
                    
            templates_to_register[key] = template_data
    
    # Add specialized templates if requested
    if specialized:
        for key in DEFAULT_TEMPLATES:
            if key not in templates_to_register and key.startswith("flopynet-"):
                templates_to_register[key] = DEFAULT_TEMPLATES[key].copy()
    
    # Register the templates
    return register_templates(api, templates_to_register, registry)

def register_custom_templates(api, templates: Dict[str, Dict[str, Any]], registry: str = "abdulmelink") -> Dict[str, bool]:
    """
    Register custom templates in GNS3.
    
    Args:
        api: GNS3 API instance
        templates: Dictionary of custom template definitions
        registry: Docker registry to use (default: abdulmelink)
        
    Returns:
        Dict[str, bool]: Dictionary of template keys and success status
    """
    return register_templates(api, templates, registry)

def get_template_by_name(api, name: str) -> Optional[Dict[str, Any]]:
    """
    Get a template by name.
    
    Args:
        api: GNS3 API instance
        name: Template name
        
    Returns:
        Optional[Dict[str, Any]]: Template data or None if not found
    """
    success, templates = get_templates_from_api(api)
    if not success:
        return None
    
    for template in templates:
        if isinstance(template, dict) and template.get('name', '').lower() == name.lower():
            return template
    
    return None

def delete_template(api, template_id: str) -> bool:
    """
    Delete a template by ID.
    
    Args:
        api: GNS3 API instance
        template_id: Template ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if hasattr(api, 'delete_template'):
            success, result = api.delete_template(template_id)
            return success
        else:
            logger.error("API instance does not have delete_template method")
            return False
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        return False

def clean_templates(api, pattern: str = "flopynet") -> int:
    """
    Clean (delete) all templates matching a pattern.
    
    Args:
        api: GNS3 API instance
        pattern: Pattern to match in template names (default: flopynet)
        
    Returns:
        int: Number of templates deleted
    """
    success, templates = get_templates_from_api(api)
    if not success or not templates:
        return 0
    
    count = 0
    for template in templates:
        if pattern.lower() in template.get('name', '').lower():
            template_id = template.get('template_id')
            if template_id:
                if delete_template(api, template_id):
                    count += 1
                    logger.info(f"Deleted template: {template.get('name')}")
    
    return count 