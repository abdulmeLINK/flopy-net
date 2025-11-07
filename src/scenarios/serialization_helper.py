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

"""
Helper functions for serializing scenario objects.

This module provides utility functions to make scenario objects serializable
for API responses.
"""

import logging
import inspect
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def is_serializable(obj: Any) -> bool:
    """
    Check if an object is JSON serializable.
    
    Args:
        obj: The object to check
        
    Returns:
        True if the object is serializable, False otherwise
    """
    if obj is None:
        return True
    elif isinstance(obj, (str, int, float, bool)):
        return True
    elif isinstance(obj, (list, tuple)):
        return all(is_serializable(item) for item in obj)
    elif isinstance(obj, dict):
        return all(isinstance(k, str) and is_serializable(v) for k, v in obj.items())
    else:
        return False

def extract_serializable_attributes(obj: Any) -> Dict[str, Any]:
    """
    Extract serializable attributes from an object.
    
    Args:
        obj: The object to extract attributes from
        
    Returns:
        Dictionary of serializable attributes
    """
    result = {}
    
    # Try different approaches to extract attributes
    try:
        # First try to convert directly to dict if possible
        if hasattr(obj, '__dict__'):
            for key, value in vars(obj).items():
                if not key.startswith('_') and is_serializable(value):
                    result[key] = value
        
        # Get common attributes that might be properties
        common_attributes = ['status', 'name', 'id', 'type', 'results', 'error', 'config']
        for attr in common_attributes:
            if hasattr(obj, attr):
                try:
                    value = getattr(obj, attr)
                    if is_serializable(value):
                        result[attr] = value
                except:
                    pass
        
        # If it's a module with members, extract classes and functions
        if inspect.ismodule(obj):
            for name, member in inspect.getmembers(obj):
                if not name.startswith('_') and (inspect.isclass(member) or inspect.isfunction(member)):
                    result[name] = member.__name__
    except Exception as e:
        logger.error(f"Error extracting attributes from object: {e}")
    
    return result

def make_scenario_serializable(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a scenario status dictionary serializable by removing non-serializable objects.
    
    Args:
        scenario_data: The scenario data dictionary
        
    Returns:
        A serializable version of the scenario data
    """
    if not scenario_data:
        return {}
        
    # Create a new dictionary with serializable data
    serializable_data = {}
    
    # Copy all serializable items
    for key, value in scenario_data.items():
        # Handle the instance which contains the actual scenario object
        if key == 'instance':
            if value is not None:
                # Extract serializable properties from the instance
                instance_data = extract_serializable_attributes(value)
                
                # Add basic info on whether components are initialized
                for component in ['policy_engine', 'network', 'server', 'clients', 'network_simulator', 'simulator']:
                    instance_data[f'{component}_initialized'] = hasattr(value, component) and getattr(value, component) is not None
                
                # Add component counts if available
                if hasattr(value, 'clients') and isinstance(value.clients, list):
                    instance_data['num_clients'] = len(value.clients)
                
                serializable_data['instance_info'] = instance_data
        elif is_serializable(value):
            # Copy if the value is directly serializable
            serializable_data[key] = value
        elif isinstance(value, dict):
            # Handle nested dictionaries
            serializable_data[key] = {k: v for k, v in value.items() if is_serializable(v)}
        elif isinstance(value, (list, tuple)):
            # Handle lists and tuples
            serializable_data[key] = [item for item in value if is_serializable(item)]
        else:
            # For other types, try to extract serializable attributes
            serializable_data[key] = extract_serializable_attributes(value)
    
    return serializable_data

def make_all_scenarios_serializable(scenarios_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Make all scenario status dictionaries serializable.
    
    Args:
        scenarios_data: Dictionary mapping scenario IDs to their status data
        
    Returns:
        A serializable version of the scenarios data
    """
    if not scenarios_data:
        return {}
        
    serializable_data = {}
    
    for scenario_id, scenario_data in scenarios_data.items():
        try:
            serializable_data[scenario_id] = make_scenario_serializable(scenario_data)
        except Exception as e:
            logger.error(f"Error serializing scenario {scenario_id}: {e}")
            # Include only basic information if serialization fails
            serializable_data[scenario_id] = {
                'id': scenario_id,
                'error': f"Serialization error: {str(e)}",
                'status': scenario_data.get('status', 'unknown')
            }
    
    return serializable_data 