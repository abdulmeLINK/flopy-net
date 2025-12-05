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
Policy Engine Server

This module implements a server for the policy engine that handles policy management and evaluation.
"""

import os
import sys

# --- Add project root to path for absolute imports ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import logging
import json
import threading
import time
import datetime
import random
from typing import Dict, Any, List, Optional, Union, Tuple
from functools import lru_cache
from flask import Flask, request, jsonify, g
from flask_cors import CORS

# --- Use absolute imports --- 
from src.core.config import ConfigManager, get_policy_engine_config
from src.policy_engine.policies import PolicyManager, Policy, PolicyEvaluationError
from src.policy_engine.policy_functions import PolicyFunctionManager, PolicyFunction, PolicyFunctionError

# --- Import event buffer utilities ---
from src.policy_engine.utils.event_buffer import (
    log_event,
    EVENT_BUFFER,
    EVENT_BUFFER_LOCK,
    MAX_EVENT_BUFFER_SIZE,
)

# --- Import API Blueprints ---
from src.policy_engine.api import (
    policy_bp,
    init_policy_routes,
    function_bp,
    init_function_routes,
    metrics_bp,
    init_metrics_routes,
)

# --- Import evaluation components ---
from src.policy_engine.evaluation.condition_evaluator import ConditionEvaluator
from src.policy_engine.evaluation.policy_checker import PolicyChecker
from src.policy_engine.evaluation.application_tracker import ApplicationTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        A dictionary containing the configuration
    """
    try:
        if not config_path or not os.path.exists(config_path):
            logger.warning(f"Configuration file not found, using default path: {config_path}")
            return {}
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {str(e)}")
        return {}

@app.route('/events', methods=['GET'])
def get_events():
    """
    Get events from the event buffer.
    
    Query parameters:
        since_event_id: Optional event ID to get events after this ID
        limit: Maximum number of events to return (default: 1000)
    """
    try:
        # Parse query parameters
        since_event_id = request.args.get('since_event_id')
        limit = int(request.args.get('limit', 1000))  # No hard maximum limit
        
        logger.debug(f"Events endpoint called - buffer size: {len(EVENT_BUFFER)}")
        
        # Lock the buffer while making a copy
        with EVENT_BUFFER_LOCK:
            # Make a snapshot to work with
            current_events = EVENT_BUFFER.copy()
            logger.debug(f"Copied {len(current_events)} events from buffer")
            
            last_event_id = current_events[-1]["id"] if current_events else None
            
            if not current_events:
                logger.debug("Event buffer is empty")
                return jsonify({"events": [], "last_event_id": None})
            
            # Filter events after since_event_id if provided
            start_index = 0
            if since_event_id:
                logger.debug(f"Filtering events after ID: {since_event_id}")
                # Find the index of the event *after* since_event_id
                found = False
                for i, event in enumerate(current_events):
                    if event["id"] == since_event_id:
                        start_index = i + 1
                        found = True
                        logger.debug(f"Found event at index {i}, returning events starting from index {start_index}")
                        break
                        
                # If since_event_id not found, return all events
                if not found:
                    logger.debug(f"Event ID not found: {since_event_id}, returning all events")
                    start_index = 0
            
            # Slice the list based on start_index and limit
            results = current_events[start_index : start_index + limit]
            logger.debug(f"Returning {len(results)} events")
        
        return jsonify({
            "events": results,
            "last_event_id": last_event_id
        })
    except Exception as e:
        logger.error(f"Error in /events endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

class PolicyEngine:
    """Policy engine for evaluating and enforcing policies."""
    
    def __init__(self):
        """Initialize the policy engine with memory optimizations."""
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.policy_history: List[Dict[str, Any]] = []
        self.policy_version = 0
        self.loaded_from_file = False
        
        # Policy function manager
        self.function_manager = PolicyFunctionManager()
        
        # Initialize evaluation components
        self.condition_evaluator = ConditionEvaluator()
        self.application_tracker = ApplicationTracker(
            max_application_history=1000,  # Reduced from 10000 for memory optimization
            cleanup_interval=3600  # Cleanup every hour
        )
        self.policy_checker = PolicyChecker(
            condition_evaluator=self.condition_evaluator,
            application_tracker=self.application_tracker,
            function_manager=self.function_manager
        )
        
        # Keep references for backward compatibility
        self.policy_applications = self.application_tracker.policy_applications
        self.policy_application_stats = self.application_tracker.policy_application_stats
        self.max_application_history = 1000
        self.max_policy_history = 500        # Limit policy history size
        
        # Memory cleanup tracking
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 3600  # Cleanup every hour
        
        # Load policies from file if it exists
        self._load_policies()
        
        logger.info("Policy engine initialized with memory optimizations")
        
        # Log engine start event
        log_event("ENGINE_START", {"version": self.policy_version, "policies_loaded": len(self.policies)})
    
    def _load_policies(self) -> None:
        """Load policies from file."""
        try:
            policy_file = os.environ.get('POLICY_FILE', os.path.join('config', 'policies', 'policies.json'))
            
            # Initialize policies dictionary
            policies_dict = {}
            
            # First load default policies if they exist
            default_policy_file = os.path.join(os.path.dirname(policy_file), 'default_policies.json')
            if os.path.exists(default_policy_file):
                try:
                    with open(default_policy_file, 'r') as f:
                        default_data = json.load(f)
                        
                        if "policies" in default_data:
                            # Add default policies to dictionary
                            for policy in default_data["policies"]:
                                if "id" in policy:
                                    policies_dict[policy["id"]] = policy
                                else:
                                    logger.warning(f"Policy without ID found in {default_policy_file}, skipping")
                        
                            logger.info(f"Loaded {len(policies_dict)} default policies from {default_policy_file}")
                except Exception as e:
                    logger.error(f"Error loading default policies from {default_policy_file}: {e}")
            
            # Then load main policies file, which may override defaults
            if os.path.exists(policy_file):
                with open(policy_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load policies
                    if "policies" in data:
                        policies_data = data["policies"]
                        
                        # Handle both array and object formats
                        if isinstance(policies_data, list):
                            # Array format: [{"id": "...", ...}, ...]
                            for policy in policies_data:
                                if "id" in policy:
                                    policies_dict[policy["id"]] = policy
                                else:
                                    logger.warning(f"Policy without ID found in {policy_file}, skipping")
                        elif isinstance(policies_data, dict):
                            # Object format: {"policy-id": {"id": "policy-id", ...}, ...}
                            for policy_id, policy in policies_data.items():
                                if isinstance(policy, dict):
                                    # Ensure the policy has an ID field
                                    if "id" not in policy:
                                        policy["id"] = policy_id
                                    policies_dict[policy_id] = policy
                                else:
                                    logger.warning(f"Invalid policy format for {policy_id} in {policy_file}, skipping")
                        else:
                            logger.error(f"Invalid policies format in {policy_file}: expected array or object, got {type(policies_data)}")
                        
                        self.policies = policies_dict
                        self.policy_version = data.get("version", 0)
                        self.policy_history = data.get("history", [])
                        self.loaded_from_file = True
                        
                        logger.info(f"Loaded {len(self.policies)} policies (total after merging defaults) from {policy_file}")
                        
                        # Log events for each loaded policy
                        for policy_id, policy in self.policies.items():
                            log_event("POLICY_LOADED", {
                                "policy_id": policy_id,
                                "policy_type": policy.get("type", "unknown"),
                                "source": "merged_policies"
                            })
                    else:
                        logger.warning(f"No policies found in {policy_file}")
            else:
                # If main policy file doesn't exist but we loaded defaults, use them
                if policies_dict:
                    self.policies = policies_dict
                    self.loaded_from_file = True
                    logger.info(f"Using {len(policies_dict)} default policies as main policy file was not found")
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
    
    def _save_policies(self) -> None:
        """Save policies to file."""
        try:
            policy_file = os.environ.get('POLICY_FILE', os.path.join('config', 'policies', 'policies.json'))
            
            data = {
                "version": self.policy_version,
                "policies": self.policies,
                "history": self.policy_history,
                "updated_at": time.time()
            }
            
            with open(policy_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved {len(self.policies)} policies to {policy_file}")
        except Exception as e:
            logger.error(f"Error saving policies: {e}")
    
    def validate_policy_data(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate policy data for common issues.
        
        Args:
            policy_data: Policy data to validate
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check required fields
        if "type" not in policy_data:
            issues.append("Missing required field: 'type'")
        
        if "rules" not in policy_data:
            issues.append("Missing required field: 'rules'")
        elif not isinstance(policy_data["rules"], list):
            issues.append("Field 'rules' must be a list")
        else:
            # Validate rules
            for i, rule in enumerate(policy_data["rules"]):
                if not isinstance(rule, dict):
                    issues.append(f"Rule {i} must be a dictionary")
                    continue
                
                # Check for action
                if "action" not in rule:
                    warnings.append(f"Rule {i} missing 'action' field, will default to 'allow'")
                elif rule["action"] not in ["allow", "deny", "configure", "log", "monitor"]:
                    warnings.append(f"Rule {i} has unknown action '{rule['action']}'")
                
                # Check match conditions
                if "match" in rule:
                    match_conditions = rule["match"]
                    if not isinstance(match_conditions, dict):
                        issues.append(f"Rule {i} 'match' field must be a dictionary")
                    else:
                        # Check for condition syntax
                        for key, value in match_conditions.items():
                            if isinstance(value, str) and any(op in value for op in ['>=', '<=', '>', '<', '!=']):
                                # Validate condition syntax
                                try:
                                    if '>=' in value:
                                        parts = value.split('>=')
                                    elif '<=' in value:
                                        parts = value.split('<=')
                                    elif '>' in value:
                                        parts = value.split('>')
                                    elif '<' in value:
                                        parts = value.split('<')
                                    elif '!=' in value:
                                        parts = value.split('!=')
                                    
                                    if len(parts) != 2:
                                        issues.append(f"Rule {i} has invalid condition syntax: '{value}'")
                                    elif not parts[1].strip():
                                        issues.append(f"Rule {i} condition missing threshold value: '{value}'")
                                except Exception:
                                    issues.append(f"Rule {i} has malformed condition: '{value}'")
        
        # Check priority
        if "priority" in policy_data:
            try:
                priority = int(policy_data["priority"])
                if priority < 0 or priority > 1000:
                    warnings.append("Priority should be between 0 and 1000")
            except (ValueError, TypeError):
                issues.append("Priority must be a number")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def create_policy(self, policy_type: str, policy_data: Dict[str, Any]) -> str:
        """
        Create a new policy with validation.
        
        Args:
            policy_type: Type of policy to create
            policy_data: Policy configuration data
            
        Returns:
            Policy ID if successful
            
        Raises:
            ValueError: If policy data is invalid
        """
        # Validate policy data
        validation_result = self.validate_policy_data(policy_data)
        
        if not validation_result["valid"]:
            error_msg = f"Policy validation failed: {'; '.join(validation_result['issues'])}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log warnings if any
        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"Policy validation warning: {warning}")
        
        # Generate policy ID
        policy_id = policy_data.get("id")
        if not policy_id:
            import uuid
            policy_id = f"{policy_type}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Ensure policy has required fields
        policy_data["type"] = policy_type
        policy_data["id"] = policy_id
        policy_data["enabled"] = policy_data.get("enabled", True)
        policy_data["created_at"] = time.time()
        policy_data["updated_at"] = time.time()
        
        # Store the policy
        self.policies[policy_id] = policy_data
        
        # Save to file
        try:
            self._save_policies()
            logger.info(f"Created policy {policy_id} of type {policy_type}")
            
            # Log policy creation event
            log_event("POLICY_CREATED", {
                "policy_id": policy_id,
                "policy_type": policy_type,
                "validation_warnings": validation_result["warnings"]
            })
            
            return policy_id
            
        except Exception as e:
            # Remove from memory if save failed
            if policy_id in self.policies:
                del self.policies[policy_id]
            logger.error(f"Failed to save policy {policy_id}: {e}")
            raise ValueError(f"Failed to save policy: {e}")
    
    def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> bool:
        """
        Update an existing policy.
        
        Args:
            policy_id: ID of the policy to update
            policy_data: New policy data
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.error(f"Policy {policy_id} not found")
            return False

        # Get existing policy
        policy = self.policies[policy_id]

        # Create copy of existing policy data for history
        # Get current data from the appropriate location
        if "data" in policy:
            old_data = policy["data"].copy()
        else:
            # Extract relevant policy data from root level for history
            old_data = {
                "rules": policy.get("rules", []),
                "description": policy.get("description", ""),
                "priority": policy.get("priority", 0),
                "type": policy.get("type", ""),
                "name": policy.get("name", "")
            }

        # Increment policy version
        self.policy_version += 1

        # CRITICAL FIX: Update policy data directly at root level for consistency
        # This ensures the policy structure remains consistent with loaded policies
        policy["updated_at"] = time.time()
        policy["version"] = self.policy_version
        
        # Update all fields directly at root level (consistent with loading)
        if "rules" in policy_data:
            policy["rules"] = policy_data["rules"]
        if "description" in policy_data:
            policy["description"] = policy_data["description"]
        if "priority" in policy_data:
            policy["priority"] = policy_data["priority"]
        if "type" in policy_data:
            policy["type"] = policy_data["type"]
        if "name" in policy_data:
            policy["name"] = policy_data["name"]
        if "enabled" in policy_data:
            policy["enabled"] = policy_data["enabled"]

        # Remove any existing 'data' field to avoid confusion
        if "data" in policy:
            del policy["data"]

        # Add policy update to history
        self.policy_history.append({
            "action": "update",
            "policy_id": policy_id,
            "timestamp": time.time(),
            "version": self.policy_version,
            "old_data": old_data,
            "new_data": policy_data
        })

        # Save policies to file
        self._save_policies()

        logger.info(f"Updated policy {policy_id} to version {self.policy_version}")
        
        # Log policy update event for monitoring
        log_event("POLICY_UPDATED", {
            "policy_id": policy_id,
            "policy_version": self.policy_version,
            "timestamp": time.time(),
            "old_version": policy.get("version", 0)
        })

        return True
    
    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete a policy.
        
        Args:
            policy_id: ID of the policy to delete
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.error(f"Policy {policy_id} not found")
            return False
        
        # Get existing policy
        policy = self.policies[policy_id]
        
        # Increment policy version
        self.policy_version += 1
        
        # Add policy deletion to history
        self.policy_history.append({
            "action": "delete",
            "policy_id": policy_id,
            "timestamp": time.time(),
            "version": self.policy_version,
            # Store the policy data for history
            "data": {
                "rules": policy.get("rules", []),
                "description": policy.get("description", ""),
                "priority": policy.get("priority", 0),
                "type": policy.get("type", ""),
                "name": policy.get("name", "")
            }
        })
        
        # Remove policy
        del self.policies[policy_id]
        
        # Save policies to file
        self._save_policies()
        
        logger.info(f"Deleted policy {policy_id}")
        
        return True
    
    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a policy by ID.
        
        Args:
            policy_id: ID of the policy
            
        Returns:
            Policy data or None if not found
        """
        if policy_id not in self.policies:
            logger.error(f"Policy {policy_id} not found")
            return None
        
        return self.policies[policy_id]
    
    def list_policies(self, policy_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all policies, optionally filtered by type.
        
        Args:
            policy_type: Type of policies to filter by
            
        Returns:
            List of policies
        """
        # Ensure self.policies is a dictionary
        if not isinstance(self.policies, dict):
            logger.warning("Policies is not a dictionary, converting...")
            if isinstance(self.policies, list):
                policies_dict = {}
                for policy in self.policies:
                    if "id" in policy:
                        policies_dict[policy["id"]] = policy
                self.policies = policies_dict
            else:
                logger.error(f"Cannot convert policies of type {type(self.policies)} to dictionary")
                return []
        
        if policy_type:
            return [p for p in self.policies.values() if p["type"] == policy_type]
        else:
            return list(self.policies.values())
    
    def enable_policy(self, policy_id: str) -> bool:
        """
        Enable a policy.
        
        Args:
            policy_id: ID of the policy to enable
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.error(f"Policy {policy_id} not found")
            return False
        
        # Get existing policy
        policy = self.policies[policy_id]
        
        # Skip if already enabled
        if policy.get("enabled", True):
            return True
        
        # Increment policy version
        self.policy_version += 1
        
        # Enable policy
        policy["enabled"] = True
        policy["updated_at"] = time.time()
        policy["version"] = self.policy_version
        
        # Add policy update to history
        self.policy_history.append({
            "action": "enable",
            "policy_id": policy_id,
            "timestamp": time.time(),
            "version": self.policy_version
        })
        
        # Save policies to file
        self._save_policies()
        
        logger.info(f"Enabled policy {policy_id}")
        
        return True
    
    def disable_policy(self, policy_id: str) -> bool:
        """
        Disable a policy.
        
        Args:
            policy_id: ID of the policy to disable
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.error(f"Policy {policy_id} not found")
            return False
        
        # Get existing policy
        policy = self.policies[policy_id]
        
        # Skip if already disabled
        if not policy.get("enabled", True):
            return True
        
        # Increment policy version
        self.policy_version += 1
        
        # Disable policy
        policy["enabled"] = False
        policy["updated_at"] = time.time()
        policy["version"] = self.policy_version
        
        # Add policy update to history
        self.policy_history.append({
            "action": "disable",
            "policy_id": policy_id,
            "timestamp": time.time(),
            "version": self.policy_version
        })
        
        # Save policies to file
        self._save_policies()
        
        logger.info(f"Disabled policy {policy_id}")
        
        return True
    
    def check_policy(self, policy_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if an operation is allowed by the policies with enhanced decision tracking.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            
        Returns:
            Dictionary with comprehensive policy decision and detailed metadata
        """
        return self.policy_checker.check_policy(
            policy_type=policy_type,
            context=context,
            policies=self.policies,
            log_event_callback=log_event,
            log_decision_callback=self.log_decision
        )

    def _evaluate_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a complex condition expression with enhanced logic. Delegates to ConditionEvaluator."""
        return self.condition_evaluator.evaluate_condition(condition, context, parameters)
    
    def _evaluate_simple_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluate a simple condition expression. Delegates to ConditionEvaluator."""
        return self.condition_evaluator.evaluate_simple_condition(condition, context, parameters)
    
    def _get_value(self, expr: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Any:
        """Get the value of an expression from context or parameters. Delegates to ConditionEvaluator."""
        return self.condition_evaluator.get_value(expr, context, parameters)
    
    def _convert_to_appropriate_type(self, value: Any) -> Any:
        """Convert a value to the most appropriate type. Delegates to ConditionEvaluator."""
        return self.condition_evaluator.convert_to_appropriate_type(value)

    def _record_policy_application(self, policy_type: str, requester_id: str, component: str, 
                                   action: str, context: Dict[str, Any], result: bool,
                                   reason: str, policies_checked: List[str], policy_count: int,
                                   evaluation_time_ms: float, violations: List[Dict[str, Any]]) -> None:
        """Record a policy application for history tracking and statistics. Delegates to ApplicationTracker."""
        self.application_tracker.record_policy_application(
            policy_type=policy_type,
            requester_id=requester_id,
            component=component,
            action=action,
            context=context,
            result=result,
            reason=reason,
            policies_checked=policies_checked,
            policy_count=policy_count,
            evaluation_time_ms=evaluation_time_ms,
            violations=violations
        )
    
    def get_policy_applications(self, policy_type=None, component=None, requester_id=None, 
                               result=None, limit=100, start_time=None, end_time=None) -> List[Dict[str, Any]]:
        """Get history of policy applications with filtering options. Delegates to ApplicationTracker."""
        return self.application_tracker.get_policy_applications(
            policy_type=policy_type,
            component=component,
            requester_id=requester_id,
            result=result,
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )

    # Function-based policy methods
    def create_policy_function(self, name: str, code: str, description: str = "", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new policy function.
        
        Args:
            name: Name of the function
            code: Function code as a string
            description: Function description
            metadata: Additional metadata
            
        Returns:
            Dictionary with function information
        """
        try:
            # Create function
            function = self.function_manager.create_function(
                name=name,
                code=code,
                description=description,
                metadata=metadata
            )
            
            logger.info(f"Created policy function {name} ({function.function_id})")
            
            return function.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating policy function: {e}")
            raise
    
    def validate_function_code(self, code: str) -> Dict[str, Any]:
        """
        Validate function code for security and correctness.
        
        Args:
            code: Function code as a string
            
        Returns:
            Dictionary with validation result
        """
        try:
            # Create a temporary function for validation
            temp_function = PolicyFunction(
                function_id="temp_validation",
                name="Temporary function for validation",
                code=code
            )
            
            # Function validation succeeded
            return {
                "valid": True,
                "message": "Function code is valid"
            }
            
        except Exception as e:
            logger.error(f"Function validation failed: {e}")
            
            return {
                "valid": False,
                "message": f"Function validation failed: {str(e)}"
            }
    
    def test_function(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test function code with the given context.
        
        Args:
            code: Function code as a string
            context: Context for function evaluation
            
        Returns:
            Dictionary with test result
        """
        try:
            # Create a temporary function for testing
            temp_function = PolicyFunction(
                function_id="temp_test",
                name="Temporary function for testing",
                code=code
            )
            
            # Evaluate the function
            result = temp_function.evaluate(context)
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Function test failed: {e}")
            
            return {
                "success": False,
                "error": str(e)
            }

    def log_decision(self, policy_id: str, context: Dict[str, Any], decision: Dict[str, Any], execution_time: float = 0.0):
        """Log a policy decision with enhanced information."""
        try:
            # Get policy details for better logging
            policy_info = self.get_policy(policy_id)
            policy_name = policy_info.get('name', policy_id) if policy_info else policy_id
            
            # Extract component information from context
            component = 'unknown'
            if 'server_id' in context:
                component = 'fl-server'
            elif 'client_id' in context:
                component = 'fl-client'
            elif 'operation' in context:
                operation = context['operation'].lower()
                if 'server' in operation:
                    component = 'fl-server'
                elif 'client' in operation:
                    component = 'fl-client'
                elif 'network' in operation:
                    component = 'network'
                elif 'policy' in operation:
                    component = 'policy-engine'
            
            # Create enhanced decision log entry
            decision_entry = {
                'id': f"decision_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
                'policy_id': policy_id,
                'policy_name': policy_name,
                'component': component,
                'timestamp': time.time(),
                'context': context,
                'decision': decision.get('action', 'unknown'),
                'result': decision.get('allowed', False),
                'reason': decision.get('reason', 'No reason provided'),
                'action_taken': decision.get('reason', 'Policy evaluation completed'),
                'execution_time': execution_time,
                'request_id': context.get('request_id', f"req_{int(time.time())}")
            }
            
            # Store in decisions history
            if not hasattr(self, 'decisions_history'):
                self.decisions_history = []
            
            self.decisions_history.append(decision_entry)
            
            # Keep only last 1000 decisions
            if len(self.decisions_history) > 1000:
                self.decisions_history = self.decisions_history[-1000:]
            
            # Send to collector if available
            if hasattr(self, 'collector_url') and self.collector_url:
                try:
                    import requests
                    requests.post(
                        f"{self.collector_url}/policy_decisions",
                        json=decision_entry,
                        timeout=5
                    )
                except Exception as e:
                    logger.debug(f"Failed to send decision to collector: {e}")
                    
        except Exception as e:
            logger.error(f"Error logging decision: {e}")
            
    def get_policy_by_id(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get policy details by ID."""
        try:
            for policy in self.policies.values():
                if policy.get('id') == policy_id:
                    return policy
            return None
        except Exception as e:
            logger.error(f"Error getting policy by ID {policy_id}: {e}")
            return None

    def _ensure_numeric_type(self, value: Any, expr_name: str) -> Union[int, float]:
        """Ensure a value is numeric, converting if necessary. Delegates to ConditionEvaluator."""
        return self.condition_evaluator.ensure_numeric_type(value, expr_name)

    def _cleanup_memory(self) -> None:
        """Clean up memory by removing old data. Delegates to ApplicationTracker."""
        self.application_tracker.cleanup_memory(self.max_policy_history)
        
        # Also clean up policy history locally
        if len(self.policy_history) > self.max_policy_history:
            keep_count = int(self.max_policy_history * 0.8)  # Keep 80%
            self.policy_history = self.policy_history[-keep_count:]
            logger.info(f"Cleaned up policy history, keeping {keep_count} recent entries")


# Create policy engine - make it global for compatibility with existing code
policy_engine = None

# API Routes are now in src/policy_engine/api/ package
# - policy_routes.py: Policy CRUD and check routes
# - function_routes.py: Function management routes
# - metrics_routes.py: Health and metrics routes

def main(args=None):
    """Main entry point for the policy engine server."""
    global policy_engine
    
    # If args not provided, parse them here
    if args is None:
        import argparse
        
        # Set up argument parser
        parser = argparse.ArgumentParser(description='Policy Engine Server')
        parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to listen on')
        parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
        parser.add_argument('--policy-file', type=str, help='Path to policy file')
        parser.add_argument('--config', type=str, help='Path to config file')
        parser.add_argument('--log-level', type=str, default='INFO', help='Logging level')
        
        args = parser.parse_args()
    
    # Configure logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    
    # Load configuration file
    config = load_config(args.config) if args.config else {}
    
    # Override config with command line arguments
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    if args.policy_file:
        config['policy_file'] = args.policy_file
    
    # Set policy file in environment for modules that might use it
    policy_file = config.get('policy_file', os.environ.get('POLICY_FILE', 'config/policies/policies.json'))
    os.environ['POLICY_FILE'] = policy_file
    
    # Log startup info
    logger.info(f"Starting Policy Engine server on {config.get('host', '0.0.0.0')}:{config.get('port', 5000)}")
    logger.info(f"Using policy file: {policy_file}")
    
    # Log config
    if args.config:
        logger.info(f"Loaded configuration from {args.config}")
    
    # Initialize the policy engine - use global instance
    policy_engine = PolicyEngine()
    app.start_time = time.time()  # Record start time for uptime calculation
    
    # Initialize API route blueprints with policy engine instance
    init_policy_routes(policy_engine)
    init_function_routes(policy_engine)
    init_metrics_routes(policy_engine)
    
    # Register blueprints with the Flask app
    app.register_blueprint(policy_bp)
    app.register_blueprint(function_bp)
    app.register_blueprint(metrics_bp)
    
    logger.info("API blueprints registered: policy_routes, function_routes, metrics_routes")
    
    # Set policy engine in Flask global context as well
    @app.before_request
    def set_policy_engine():
        g.policy_engine = policy_engine
      
    # Start the server
    app.run(
        host=config.get('host', '0.0.0.0'),
        port=config.get('port', 5000),
        debug=config.get('debug', False)
    )


if __name__ == '__main__':
    main() 