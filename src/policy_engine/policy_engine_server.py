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
import uuid
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
# from .policies import PolicyManager, Policy, PolicyEvaluationError
# from .policy_functions import PolicyFunctionManager, PolicyFunction, PolicyFunctionError
from src.policy_engine.policies import PolicyManager, Policy, PolicyEvaluationError
from src.policy_engine.policy_functions import PolicyFunctionManager, PolicyFunction, PolicyFunctionError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Event buffer for logging policy events - OPTIMIZED FOR MEMORY
MAX_EVENT_BUFFER_SIZE = 500  # Reduced from 1000
EVENT_BUFFER = []
EVENT_BUFFER_LOCK = threading.Lock()

def log_event(event_type: str, details: Dict[str, Any], source_component: str = "POLICY_ENGINE"):
    """
    Log an event to the event buffer with memory optimization.
    
    Args:
        event_type: Type of event
        details: Event-specific details dictionary
        source_component: Source component name
    """
    event_id = str(uuid.uuid4())
    timestamp = time.time()
    
    # Create compact event object
    event = {
        "id": event_id,
        "type": event_type,
        "timestamp": timestamp,
        "source": source_component,
        "details": details if isinstance(details, dict) and len(str(details)) < 1000 else {"summary": str(details)[:500]}  # Limit detail size
    }
    
    # Add to event buffer with automatic cleanup
    with EVENT_BUFFER_LOCK:
        EVENT_BUFFER.append(event)
        # Trim buffer more aggressively to save memory
        if len(EVENT_BUFFER) > MAX_EVENT_BUFFER_SIZE:
            # Remove oldest 20% of events
            remove_count = max(1, MAX_EVENT_BUFFER_SIZE // 5)
            EVENT_BUFFER[:remove_count] = []
            
    # Log the event (reduced verbosity)
    logger.debug(f"Event logged: {event_type}")
    
    return event_id

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
        
        # Add policy application tracking with memory limits
        self.policy_applications: List[Dict[str, Any]] = []
        self.policy_application_stats = {
            "total_checks": 0,
            "allowed_checks": 0,
            "denied_checks": 0,
            "by_component": {},
            "by_policy_type": {},
            "by_requester": {}
        }
        self.max_application_history = 1000  # Reduced from 10000 for memory optimization
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
        start_time = time.time()
        
        # Extract context information
        requester_id = context.get("requester_id", "unknown")
        component = context.get("component", "unknown")
        
        # Get matching policies
        matching_policies = [p for p in self.policies.values() if p.get("type") == policy_type]
        
        if not matching_policies:
            logger.warning(f"No policies found of type {policy_type}")
            result = {
                "allowed": True,  # Default to allowing if no policies found
                "reason": f"No policies of type {policy_type} found",
                "policies_checked": [],
                "violations": [],
                "rule_evaluations": [],
                "applied_actions": [],
                "decision_path": ["no_policies_found"],
                "evaluation_details": {
                    "total_policies": 0,
                    "matched_policies": 0,
                    "evaluated_rules": 0,
                    "matched_rules": 0
                }
            }
            
            # Record this policy application
            self._record_policy_application(
                policy_type=policy_type,
                requester_id=requester_id,
                component=component,
                action=context.get("action", "unknown"),
                context=context,
                result=True,
                reason=result["reason"],
                policies_checked=[],
                policy_count=0,
                evaluation_time_ms=(time.time() - start_time) * 1000,
                violations=[]
            )
            
            # Log policy evaluation result
            log_event("POLICY_EVAL_RESULT", {
                "request_id": context.get("request_id", f"req_{int(time.time())}"),
                "policy_type": policy_type,
                "result": result,
                "elapsed_ms": (time.time() - start_time) * 1000
            })
            
            return result
        
        # Enhanced tracking for detailed decision information
        violations = []
        rule_evaluations = []
        applied_actions = []
        decision_path = []
        checked_count = 0
        checked_policies = []
        total_rules_evaluated = 0
        matched_rules_count = 0
        
        # Collect parameters from configure actions
        collected_parameters = {}
        
        # Sort policies by priority (higher priority first)
        matching_policies.sort(key=lambda p: p.get("priority", 0), reverse=True)
        
        # Check each policy
        for policy in matching_policies:
            # Skip disabled policies
            if not policy.get("enabled", True):
                continue
            
            checked_count += 1
            policy_id = policy["id"]
            policy_name = policy.get("name", policy_id)
            checked_policies.append(policy_id)
            
            policy_start_time = time.time()
            
            # Use the policy directly (consistent structure after update fix)
            policy_data = policy
            
            # Track policy-level evaluation
            policy_evaluation = {
                "policy_id": policy_id,
                "policy_name": policy_name,
                "policy_type": policy_data.get("type", policy_type),
                "priority": policy.get("priority", 0),
                "rules_evaluated": [],
                "matched_rules": [],
                "actions_applied": [],
                "evaluation_time_ms": 0,
                "result": "pending"
            }
            
            # Check if the policy has a function reference
            if "function_id" in policy_data:
                try:
                    # Evaluate function-based policy
                    function_id = policy_data["function_id"]
                    function_result = self.function_manager.evaluate_function(function_id, context)
                    
                    # Record function evaluation
                    rule_eval = {
                        "rule_index": 0,
                        "rule_type": "function",
                        "function_id": function_id,
                        "matched": not function_result.get("allowed", True),
                        "action": "deny" if not function_result.get("allowed", True) else "allow",
                        "reason": function_result.get("reason", "Function evaluation"),
                        "parameters": function_result.get("parameters", {}),
                        "evaluation_time_ms": 0
                    }
                    
                    policy_evaluation["rules_evaluated"].append(rule_eval)
                    total_rules_evaluated += 1
                    
                    # If not allowed, add to violations
                    if not function_result.get("allowed", True):
                        matched_rules_count += 1
                        policy_evaluation["matched_rules"].append(rule_eval)
                        
                        violation = {
                            "policy_id": policy_id,
                            "policy_name": policy_name,
                            "rule_index": 0,
                            "rule_type": "function",
                            "action": "deny",
                            "reason": function_result.get("reason", "Function evaluation failed"),
                            "details": function_result.get("violations", []),
                            "function_id": function_id
                        }
                        violations.append(violation)
                        decision_path.append(f"policy:{policy_id}:function:{function_id}:deny")
                        
                        applied_actions.append({
                            "action": "deny",
                            "policy_id": policy_id,
                            "policy_name": policy_name,
                            "rule_index": 0,
                            "reason": violation["reason"],
                            "parameters": function_result.get("parameters", {})
                        })
                        
                        policy_evaluation["result"] = "deny"
                        
                except PolicyFunctionError as e:
                    logger.error(f"Error evaluating function for policy {policy_id}: {e}")
                    violation = {
                        "policy_id": policy_id,
                        "policy_name": policy_name,
                        "rule_index": 0,
                        "rule_type": "function_error",
                        "action": "deny",
                        "reason": f"Function evaluation error: {str(e)}",
                        "details": ["function_evaluation_error"],
                        "function_id": function_id
                    }
                    violations.append(violation)
                    decision_path.append(f"policy:{policy_id}:function_error")
                    
            # Check if the policy has a function code embedded
            elif "function_code" in policy_data:
                try:
                    # Create a temporary function for evaluation
                    temp_function = PolicyFunction(
                        function_id=f"temp_{policy_id}",
                        name=f"Temporary function for policy {policy_id}",
                        code=policy_data["function_code"]
                    )
                    
                    # Evaluate the function
                    function_result = temp_function.evaluate(context)
                    
                    # Record function evaluation
                    rule_eval = {
                        "rule_index": 0,
                        "rule_type": "embedded_function",
                        "matched": not function_result.get("allowed", True),
                        "action": "deny" if not function_result.get("allowed", True) else "allow",
                        "reason": function_result.get("reason", "Embedded function evaluation"),
                        "parameters": function_result.get("parameters", {}),
                        "evaluation_time_ms": 0
                    }
                    
                    policy_evaluation["rules_evaluated"].append(rule_eval)
                    total_rules_evaluated += 1
                    
                    # If not allowed, add to violations
                    if not function_result.get("allowed", True):
                        matched_rules_count += 1
                        policy_evaluation["matched_rules"].append(rule_eval)
                        
                        violation = {
                            "policy_id": policy_id,
                            "policy_name": policy_name,
                            "rule_index": 0,
                            "rule_type": "embedded_function",
                            "action": "deny",
                            "reason": function_result.get("reason", "Function evaluation failed"),
                            "details": function_result.get("violations", [])
                        }
                        violations.append(violation)
                        decision_path.append(f"policy:{policy_id}:embedded_function:deny")
                        
                        applied_actions.append({
                            "action": "deny",
                            "policy_id": policy_id,
                            "policy_name": policy_name,
                            "rule_index": 0,
                            "reason": violation["reason"],
                            "parameters": function_result.get("parameters", {})
                        })
                        
                        policy_evaluation["result"] = "deny"
                        
                except PolicyFunctionError as e:
                    logger.error(f"Error evaluating embedded function for policy {policy_id}: {e}")
                    violation = {
                        "policy_id": policy_id,
                        "policy_name": policy_name,
                        "rule_index": 0,
                        "rule_type": "embedded_function_error",
                        "action": "deny",
                        "reason": f"Function evaluation error: {str(e)}",
                        "details": ["function_evaluation_error"]
                    }
                    violations.append(violation)
                    decision_path.append(f"policy:{policy_id}:embedded_function_error")
                    
            # Otherwise, check using the policy data directly
            else:
                # Get rules from policy data
                rules = policy_data.get("rules", [])
                
                # Check each rule
                for rule_index, rule in enumerate(rules):
                    rule_start_time = time.time()
                    total_rules_evaluated += 1
                    
                    # Skip rules without match conditions
                    if "match" not in rule:
                        rule_eval = {
                            "rule_index": rule_index,
                            "rule_type": "no_match_condition",
                            "matched": False,
                            "action": rule.get("action", "unknown"),
                            "reason": "Rule has no match conditions",
                            "parameters": rule.get("parameters", {}),
                            "evaluation_time_ms": (time.time() - rule_start_time) * 1000
                        }
                        policy_evaluation["rules_evaluated"].append(rule_eval)
                        continue
                        
                    match_conditions = rule.get("match", {})
                    action = rule.get("action", "").lower()
                    rule_parameters = rule.get("parameters", {})
                    rule_description = rule.get("description", f"Rule {rule_index}")
                    
                    # Check if all match conditions are satisfied
                    match = True
                    match_details = []
                    
                    for key, value in match_conditions.items():
                        if key == "condition":
                            # Handle complex condition expressions
                            condition_matched, condition_reason = self._evaluate_condition(value, context, rule_parameters)
                            if not condition_matched:
                                match = False
                            match_details.append({
                                "condition_key": "condition",
                                "expected_value": value,
                                "actual_value": "evaluated_expression",
                                "matched": condition_matched,
                                "reason": condition_reason
                            })
                        else:
                            # Simple key-value matching
                            context_value = context.get(key)
                            condition_matched = context_value == value
                            condition_reason = f"Expected {key}={value}, got {context_value}"
                            
                            if not condition_matched:
                                match = False
                            
                            match_details.append({
                                "condition_key": key,
                                "expected_value": value,
                                "actual_value": context.get(key, "NOT_FOUND"),
                                "matched": condition_matched,
                                "reason": condition_reason
                            })
                    
                    # Create detailed rule evaluation record
                    rule_eval = {
                        "rule_index": rule_index,
                        "rule_type": action,
                        "description": rule_description,
                        "matched": match,
                        "action": action,
                        "reason": rule_description if match else f"Rule conditions not met: {[d['reason'] for d in match_details if not d['matched']]}",
                        "parameters": rule_parameters,
                        "match_details": match_details,
                        "evaluation_time_ms": (time.time() - rule_start_time) * 1000
                    }
                    
                    policy_evaluation["rules_evaluated"].append(rule_eval)
                    
                    # If all conditions match, process the action
                    if match:
                        matched_rules_count += 1
                        policy_evaluation["matched_rules"].append(rule_eval)
                        decision_path.append(f"policy:{policy_id}:rule:{rule_index}:{action}")
                        
                        # Enhanced action processing with comprehensive action types
                        if action in ["deny", "block", "reject", "forbid", "quarantine", "isolate", "suspend"]:
                            violation = {
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "rule_type": action,
                                "action": action,
                                "reason": rule_description,
                                "details": [action, rule_description],
                                "match_details": match_details,
                                "parameters": rule_parameters
                            }
                            violations.append(violation)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                            policy_evaluation["result"] = action
                            
                        elif action in ["configure", "modify", "adjust", "tune", "set"]:
                            # Collect parameters from matching configure rules
                            logger.debug(f"Policy {policy_id} rule {rule_index} matched configure rule. Parameters: {rule_parameters}")
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["allow", "permit", "grant", "authorize"]:
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["log", "audit", "record", "track"]:
                            # Log the action but don't affect the decision
                            logger.info(f"Policy {policy_id} rule {rule_index}: {rule_description}")
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["monitor", "watch", "observe", "inspect"]:
                            # Monitoring action - doesn't affect decision but triggers monitoring
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["throttle", "limit", "restrict"]:
                            # Rate limiting action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["prioritize", "boost", "elevate"]:
                            # Priority action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["filter", "select", "choose"]:
                            # Filter action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["enforce", "apply", "implement"]:
                            # Enforcement action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["verify", "validate", "check", "confirm"]:
                            # Verification action - requires additional validation
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["retry", "repeat", "reattempt"]:
                            # Retry action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["checkpoint", "save", "backup"]:
                            # Checkpoint action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["failover", "fallback", "redirect"]:
                            # Failover action
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["simulate", "test", "mock"]:
                            # Simulation action
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        elif action in ["rate_limit", "distribute", "reroute", "scale"]:
                            # Advanced traffic management actions
                            collected_parameters.update(rule_parameters)
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": rule_description,
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
                            
                        else:
                            # Unknown action - treat as informational
                            logger.warning(f"Unknown action '{action}' in policy {policy_id} rule {rule_index}")
                            
                            applied_actions.append({
                                "action": action,
                                "policy_id": policy_id,
                                "policy_name": policy_name,
                                "rule_index": rule_index,
                                "reason": f"Unknown action: {rule_description}",
                                "parameters": rule_parameters,
                                "match_details": match_details
                            })
            
            # Complete policy evaluation timing
            policy_evaluation["evaluation_time_ms"] = (time.time() - policy_start_time) * 1000
            policy_evaluation["actions_applied"] = [action for action in applied_actions if action["policy_id"] == policy_id]
            
            if policy_evaluation["result"] == "pending":
                policy_evaluation["result"] = "allow" if not violations else "deny"
            
            rule_evaluations.append(policy_evaluation)
        
        # Determine overall result
        allowed = len(violations) == 0
        
        # Determine primary reason
        if violations:
            primary_violation = violations[0]  # First violation (highest priority policy)
            primary_reason = f"Policy '{primary_violation['policy_name']}' rule {primary_violation['rule_index']}: {primary_violation['reason']}"
        elif applied_actions:
            configure_actions = [a for a in applied_actions if a["action"] in ["configure", "modify", "adjust", "tune", "set"]]
            if configure_actions:
                primary_reason = f"Configuration applied from {len(configure_actions)} rule(s)"
            else:
                primary_reason = f"Allowed by {len(applied_actions)} rule(s)"
        else:
            primary_reason = "No matching rules found, default allow"
        
        # Create comprehensive result
        result = {
            "allowed": allowed,
            "reason": primary_reason,
            "policies_checked": checked_count,
            "evaluation_time": time.time() - start_time,
            "rule_evaluations": rule_evaluations,
            "applied_actions": applied_actions,
            "decision_path": decision_path,
            "evaluation_details": {
                "total_policies": len(matching_policies),
                "matched_policies": len([p for p in rule_evaluations if p["matched_rules"]]),
                "evaluated_rules": total_rules_evaluated,
                "matched_rules": matched_rules_count,
                "policy_priorities": [p.get("priority", 0) for p in matching_policies]
            }
        }
        
        # Add collected parameters if any were found
        if collected_parameters:
            result["parameters"] = collected_parameters
            logger.info(f"Added parameters to policy check result: {collected_parameters}")
        
        # Add violations if any
        if violations:
            result["violations"] = violations
        
        logger.info(f"Policy check result for {policy_type}: allowed={allowed}, rules_evaluated={total_rules_evaluated}, matched_rules={matched_rules_count}")
        
        # Track this policy application
        self._record_policy_application(
            policy_type=policy_type,
            requester_id=requester_id,
            component=component,
            action=context.get("action", "unknown"),
            context=context,
            result=allowed,
            reason=result["reason"],
            policies_checked=checked_policies,
            policy_count=checked_count,
            evaluation_time_ms=(time.time() - start_time) * 1000,
            violations=violations
        )
        
        # Log enhanced decision for each policy checked
        for policy_evaluation in rule_evaluations:
            decision_data = {
                "allowed": allowed,
                "action": "allow" if allowed else "deny",
                "reason": primary_reason,
                "rule_evaluations": policy_evaluation["rules_evaluated"],
                "matched_rules": policy_evaluation["matched_rules"],
                "actions_applied": policy_evaluation["actions_applied"]
            }
            self.log_decision(policy_evaluation["policy_id"], context, decision_data, policy_evaluation["evaluation_time_ms"])

        # Log policy evaluation result
        log_event("POLICY_EVAL_RESULT", {
            "request_id": context.get("request_id", f"req_{int(time.time())}"),
            "policy_type": policy_type,
            "result": result,
            "elapsed_ms": (time.time() - start_time) * 1000
        })
        
        return result

    def _evaluate_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate a complex condition expression with enhanced logic.
        
        Args:
            condition: The condition string to evaluate
            context: Context variables
            parameters: Rule parameters for variable substitution
            
        Returns:
            Tuple of (condition_result, explanation)
        """
        try:
            # Only replace parameter placeholders with actual values, not context variables
            # Context variables will be resolved by _get_value with proper type conversion
            evaluated_condition = condition
            for param_key, param_value in parameters.items():
                # Only replace if it's a clear parameter placeholder (not a variable name)
                if param_key in evaluated_condition:
                    evaluated_condition = evaluated_condition.replace(param_key, str(param_value))
            
            # Handle common operators and expressions
            if " AND " in evaluated_condition:
                parts = evaluated_condition.split(" AND ")
                results = []
                for part in parts:
                    part_result, part_reason = self._evaluate_simple_condition(part.strip(), context, parameters)
                    results.append((part_result, part_reason))
                
                all_true = all(r[0] for r in results)
                reasons = [r[1] for r in results]
                return all_true, f"AND condition: {' AND '.join(reasons)}"
                
            elif " OR " in evaluated_condition:
                parts = evaluated_condition.split(" OR ")
                results = []
                for part in parts:
                    part_result, part_reason = self._evaluate_simple_condition(part.strip(), context, parameters)
                    results.append((part_result, part_reason))
                
                any_true = any(r[0] for r in results)
                reasons = [r[1] for r in results]
                return any_true, f"OR condition: {' OR '.join(reasons)}"
            
            else:
                return self._evaluate_simple_condition(evaluated_condition, context, parameters)
                
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False, f"Condition evaluation error: {str(e)}"
    
    def _evaluate_simple_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate a simple condition expression.
        
        Args:
            condition: Simple condition string (e.g., "x >= 5")
            context: Context variables
            parameters: Rule parameters
            
        Returns:
            Tuple of (result, explanation)
        """
        try:
            # Handle comparison operators
            operators = [">=", "<=", "==", "!=", ">", "<"]
            
            for op in operators:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    
                    # Get left value
                    left_val = self._get_value(left, context, parameters)
                    right_val = self._get_value(right, context, parameters)
                    
                    # Enhanced type handling for comparisons
                    try:
                        # For numeric comparisons, ensure both values are numeric
                        if op in [">", "<", ">=", "<="]:
                            left_val = self._ensure_numeric_type(left_val, left)
                            right_val = self._ensure_numeric_type(right_val, right)
                        
                        # Perform comparison
                        if op == ">=":
                            result = left_val >= right_val
                        elif op == "<=":
                            result = left_val <= right_val
                        elif op == "==":
                            result = left_val == right_val
                        elif op == "!=":
                            result = left_val != right_val
                        elif op == ">":
                            result = left_val > right_val
                        elif op == "<":
                            result = left_val < right_val
                        
                        return result, f"{left}({left_val}) {op} {right}({right_val}) = {result}"
                        
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Type conversion failed for condition '{condition}': {e}. Left: {left_val} ({type(left_val)}), Right: {right_val} ({type(right_val)})")
                        # For type errors, try string comparison as fallback for == and !=
                        if op in ["==", "!="]:
                            str_left = str(left_val)
                            str_right = str(right_val)
                            if op == "==":
                                result = str_left == str_right
                            else:
                                result = str_left != str_right
                            return result, f"{left}('{str_left}') {op} {right}('{str_right}') = {result} (string comparison)"
                        else:
                            # For numeric comparisons that fail, return False
                            return False, f"Type comparison error: {left}({left_val}, {type(left_val)}) {op} {right}({right_val}, {type(right_val)})"
            
            # If no operator found, treat as boolean
            bool_val = self._get_value(condition, context, parameters)
            return bool(bool_val), f"{condition} = {bool_val}"
            
        except Exception as e:
            logger.error(f"Error evaluating simple condition '{condition}': {e}")
            return False, f"Simple condition error: {str(e)}"
    
    def _get_value(self, expr: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Any:
        """
        Get the value of an expression from context or parameters with proper type conversion.
        
        Args:
            expr: Expression to evaluate
            context: Context variables
            parameters: Rule parameters
            
        Returns:
            The evaluated value with appropriate type conversion
        """
        expr = expr.strip()
        
        # First try to get from context
        if expr in context:
            value = context[expr]
            converted_value = self._convert_to_appropriate_type(value)
            # Only log if there's a type conversion issue
            if type(value) != type(converted_value):
                logger.debug(f"Type conversion for '{expr}': {value} ({type(value)}) -> {converted_value} ({type(converted_value)})")
            return converted_value
        
        # Then try to get from parameters
        if expr in parameters:
            value = parameters[expr]
            converted_value = self._convert_to_appropriate_type(value)
            # Only log if there's a type conversion issue
            if type(value) != type(converted_value):
                logger.debug(f"Type conversion for '{expr}': {value} ({type(value)}) -> {converted_value} ({type(converted_value)})")
            return converted_value
        
        # Finally try to convert the expression itself to a number
        converted_value = self._convert_to_appropriate_type(expr)
        # Only log if it's not a simple literal conversion
        if expr != str(converted_value):
            logger.debug(f"Literal conversion '{expr}' -> {converted_value} ({type(converted_value)})")
        return converted_value
    
    def _convert_to_appropriate_type(self, value: Any) -> Any:
        """
        Convert a value to the most appropriate type (int, float, bool, or string).
        
        Args:
            value: The value to convert
            
        Returns:
            The value converted to the most appropriate type
        """
        # If it's already a number or boolean, return as-is
        if isinstance(value, (int, float, bool)):
            return value
        
        # If it's not a string, return as-is
        if not isinstance(value, str):
            return value
        
        # Try to convert string to appropriate type
        value_str = value.strip()
        
        # Handle empty strings
        if not value_str:
            return None
        
        # Handle boolean values
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'
        
        # Handle None/null values
        if value_str.lower() in ('none', 'null'):
            return None
        
        # Try to convert to number
        try:
            # Check if it looks like a float
            if '.' in value_str or 'e' in value_str.lower():
                converted = float(value_str)
                # Check for special float values
                if converted != converted:  # NaN check
                    logger.warning(f"Converted string '{value_str}' to NaN, returning 0")
                    return 0.0
                return converted
            else:
                # Try int first, then float if int fails
                try:
                    return int(value_str)
                except ValueError:
                    converted = float(value_str)
                    # Check for special float values
                    if converted != converted:  # NaN check
                        logger.warning(f"Converted string '{value_str}' to NaN, returning 0")
                        return 0.0
                    return converted
        except ValueError:
            # If conversion fails, return as string
            # Only log if it looks like it should have been a number
            if any(c.isdigit() for c in value_str):
                logger.debug(f"Could not convert '{value_str}' to numeric type, keeping as string")
            return value_str

    def _record_policy_application(self, policy_type: str, requester_id: str, component: str, 
                                   action: str, context: Dict[str, Any], result: bool,
                                   reason: str, policies_checked: List[str], policy_count: int,
                                   evaluation_time_ms: float, violations: List[Dict[str, Any]]) -> None:
        """Record a policy application for history tracking and statistics."""
        timestamp = time.time()
        
        # Create application record with filtered context (exclude sensitive data)
        application_record = {
            "timestamp": timestamp,
            "iso_time": datetime.datetime.now().isoformat(),
            "policy_type": policy_type,
            "requester_id": requester_id,
            "component": component,
            "action": action,
            "context": {k: v for k, v in context.items() if k not in ['password', 'token', 'secret', 'sensitive_data']},
            "result": result,
            "reason": reason,
            "policies_checked": policies_checked,
            "policy_count": policy_count,
            "evaluation_time_ms": evaluation_time_ms,
            "violations": violations if violations else []
        }
        
        # Update statistics
        self.policy_application_stats["total_checks"] += 1
        if result:
            self.policy_application_stats["allowed_checks"] += 1
        else:
            self.policy_application_stats["denied_checks"] += 1
        
        # Update component stats
        if component not in self.policy_application_stats["by_component"]:
            self.policy_application_stats["by_component"][component] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_component"][component]["total"] += 1
        if result:
            self.policy_application_stats["by_component"][component]["allowed"] += 1
        else:
            self.policy_application_stats["by_component"][component]["denied"] += 1
        
        # Update policy type stats
        if policy_type not in self.policy_application_stats["by_policy_type"]:
            self.policy_application_stats["by_policy_type"][policy_type] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_policy_type"][policy_type]["total"] += 1
        if result:
            self.policy_application_stats["by_policy_type"][policy_type]["allowed"] += 1
        else:
            self.policy_application_stats["by_policy_type"][policy_type]["denied"] += 1
        
        # Update requester stats
        if requester_id not in self.policy_application_stats["by_requester"]:
            self.policy_application_stats["by_requester"][requester_id] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_requester"][requester_id]["total"] += 1
        if result:
            self.policy_application_stats["by_requester"][requester_id]["allowed"] += 1
        else:
            self.policy_application_stats["by_requester"][requester_id]["denied"] += 1
        
        # Add to history with size limit
        self.policy_applications.append(application_record)
        if len(self.policy_applications) > self.max_application_history:
            self.policy_applications = self.policy_applications[-self.max_application_history:]
        
        # Periodic memory cleanup (every 100 applications)
        if len(self.policy_applications) % 100 == 0:
            self._cleanup_memory()
        
        logger.debug(f"Recorded policy application: {policy_type} for {component} by {requester_id}")
    
    def get_policy_applications(self, policy_type=None, component=None, requester_id=None, 
                               result=None, limit=100, start_time=None, end_time=None) -> List[Dict[str, Any]]:
        """
        Get history of policy applications with filtering options.
        
        Args:
            policy_type: Filter by policy type
            component: Filter by component name
            requester_id: Filter by requester ID
            result: Filter by result (True/False)
            limit: Maximum number of results to return
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of policy applications
        """
        # Get applications history
        applications = self.policy_applications
        
        # Apply filters
        if policy_type:
            applications = [a for a in applications if a.get('policy_type') == policy_type]
        if component:
            applications = [a for a in applications if a.get('component') == component]
        if requester_id:
            applications = [a for a in applications if a.get('requester_id') == requester_id]
        if result is not None:
            applications = [a for a in applications if a.get('result') == result]
        if start_time:
            try:
                start_timestamp = float(start_time)
                applications = [a for a in applications if a.get('timestamp') >= start_timestamp]
            except (ValueError, TypeError):
                pass
        if end_time:
            try:
                end_timestamp = float(end_time)
                applications = [a for a in applications if a.get('timestamp') <= end_timestamp]
            except (ValueError, TypeError):
                pass
        
        # Sort by timestamp (newest first) and limit results
        applications = sorted(applications, key=lambda x: x.get('timestamp', 0), reverse=True)[:limit]
        
        return applications

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
        """
        Ensure a value is numeric, converting if necessary.
        
        Args:
            value: The value to convert
            expr_name: Name of the expression for error reporting
            
        Returns:
            Numeric value (int or float)
            
        Raises:
            ValueError: If the value cannot be converted to a number
        """
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, bool):
            return int(value)
        
        if isinstance(value, str):
            value_str = value.strip()
            
            # Handle special string values
            if value_str.lower() in ('true', '1'):
                return 1
            elif value_str.lower() in ('false', '0'):
                return 0
            elif value_str.lower() in ('none', 'null', ''):
                return 0
            
            # Try to convert to number
            try:
                if '.' in value_str or 'e' in value_str.lower():
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                raise ValueError(f"Cannot convert '{value_str}' to numeric value for expression '{expr_name}'")
        
        # Try to convert other types
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {type(value)} value '{value}' to numeric for expression '{expr_name}'")

    def _cleanup_memory(self) -> None:
        """Clean up memory by removing old data."""
        current_time = time.time()
        
        # Only cleanup if enough time has passed
        if current_time - self._last_cleanup_time < self._cleanup_interval:
            return
        
        try:
            # Cleanup policy applications
            if len(self.policy_applications) > self.max_application_history:
                # Keep only recent applications
                keep_count = int(self.max_application_history * 0.8)  # Keep 80%
                self.policy_applications = self.policy_applications[-keep_count:]
                logger.info(f"Cleaned up policy applications, keeping {keep_count} recent entries")
            
            # Cleanup policy history
            if len(self.policy_history) > self.max_policy_history:
                keep_count = int(self.max_policy_history * 0.8)  # Keep 80%
                self.policy_history = self.policy_history[-keep_count:]
                logger.info(f"Cleaned up policy history, keeping {keep_count} recent entries")
            
            # Cleanup component stats (keep only top 50 components)
            if len(self.policy_application_stats["by_component"]) > 50:
                # Sort by usage and keep top components
                sorted_components = sorted(
                    self.policy_application_stats["by_component"].items(),
                    key=lambda x: x[1].get("total", 0),
                    reverse=True
                )[:50]
                self.policy_application_stats["by_component"] = dict(sorted_components)
            
            # Similar cleanup for requesters
            if len(self.policy_application_stats["by_requester"]) > 100:
                sorted_requesters = sorted(
                    self.policy_application_stats["by_requester"].items(),
                    key=lambda x: x[1].get("total", 0),
                    reverse=True
                )[:100]
                self.policy_application_stats["by_requester"] = dict(sorted_requesters)
            
            self._last_cleanup_time = current_time
            logger.debug("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")

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
    

# Create policy engine - make it global for compatibility with existing code
policy_engine = None

# API Routes

@app.route('/api/v1/policies', methods=['GET'])
def list_policies():
    """List all policies."""
    try:
        policy_type = request.args.get('type')
        
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        policies = pe.list_policies(policy_type)
        return jsonify(policies)
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    """Get a policy by ID."""
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        policy = pe.get_policy(policy_id)
        if policy:
            return jsonify(policy)
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error getting policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/policies', methods=['POST'])
def create_policy():
    """Create a new policy."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    policy_type = data.get('type')
    policy_data = data.get('data')
    
    if not policy_type or not policy_data:
        return jsonify({"error": "Missing required fields: type, data"}), 400
    
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        policy_id = pe.create_policy(policy_type, policy_data)
        return jsonify({"id": policy_id}), 201
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/policies/<policy_id>', methods=['PUT'])
def update_policy(policy_id):
    """Update a policy."""
    # Use the entire JSON request body as the policy data
    policy_data = request.json
    if not policy_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Ensure policy_engine instance is available (might be set via before_request)
        pe = g.get("policy_engine", policy_engine) 
        if not pe:
             raise RuntimeError("Policy Engine instance not found in request context")
             
        success = pe.update_policy(policy_id, policy_data)

        if success:
            return jsonify({"success": True})
        else:
            # PolicyEngine.update_policy should ideally raise specific exceptions
            # For now, assume failure means not found if no exception occurred
            return jsonify({"error": "Policy not found or update failed"}), 404
            
    except PolicyEvaluationError as e: # Catch specific policy errors if defined
        logger.error(f"Policy update error for {policy_id}: {str(e)}")
        return jsonify({"error": f"Policy update error: {str(e)}"}), 400
    except Exception as e:
        logger.exception(f"Unexpected error updating policy {policy_id}: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/v1/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    """Delete a policy."""
    try:
        # Ensure policy_engine instance is available
        pe = g.get("policy_engine", policy_engine)
        if not pe:
             raise RuntimeError("Policy Engine instance not found in request context")
             
        success = pe.delete_policy(policy_id)

        if success:
            return jsonify({"success": True})
        else:
            # Assume failure means not found if no exception occurred
            return jsonify({"error": "Policy not found or delete failed"}), 404
            
    except Exception as e:
        logger.exception(f"Unexpected error deleting policy {policy_id}: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/api/v1/policies/<policy_id>/enable', methods=['POST'])
def enable_policy(policy_id):
    """Enable a policy."""
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        success = pe.enable_policy(policy_id)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error enabling policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/policies/<policy_id>/disable', methods=['POST'])
def disable_policy(policy_id):
    """Disable a policy."""
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        success = pe.disable_policy(policy_id)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Policy not found"}), 404
    except Exception as e:
        logger.error(f"Error disabling policy {policy_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/check', methods=['POST'])
def check_policy():
    try:
        # Get request data
        req_data = request.get_json()
        
        # Validate request data
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
            
        policy_type = req_data.get("policy_type")
        context = req_data.get("context", {})
        
        # Validate policy type
        if not policy_type:
            return jsonify({"error": "Invalid request: Missing policy_type"}), 400
        
        # Use globally defined policy_engine first, then fall back to Flask g if needed
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Check policy
        try:
            result = pe.check_policy(policy_type, context)
            return jsonify(result), 200
        except Exception as e:
            logger.exception(f"Error checking policy: {str(e)}")
            return jsonify({"error": f"Error checking policy: {str(e)}"}), 500
    except Exception as e:
        logger.exception(f"Exception in check_policy: {str(e)}")
        return jsonify({"error": f"Exception: {str(e)}"}), 500


# Function-based policy routes

@app.route('/api/v1/functions', methods=['GET'])
def list_functions():
    """List all policy functions."""
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        functions = pe.function_manager.list_functions()
        return jsonify(functions)
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/functions/<function_id>', methods=['GET'])
def get_function(function_id):
    """Get a policy function by ID."""
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        function = pe.function_manager.get_function(function_id)
        return jsonify(function.to_dict())
    except Exception as e:
        logger.error(f"Error getting function {function_id}: {e}")
        return jsonify({"error": str(e)}), 404


@app.route('/api/v1/functions', methods=['POST'])
def create_function():
    """Create a new policy function."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')
    metadata = data.get('metadata', {})
    
    if not name or not code:
        return jsonify({"error": "Missing required fields: name, code"}), 400
    
    try:
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        function = pe.create_policy_function(name, code, description, metadata)
        return jsonify(function), 201
    except Exception as e:
        logger.error(f"Error creating function: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/functions/<function_id>', methods=['PUT'])
def update_function(function_id):
    """Update a policy function."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        function = policy_engine.function_manager.update_function(
            function_id=function_id,
            name=data.get('name'),
            code=data.get('code'),
            description=data.get('description'),
            metadata=data.get('metadata')
        )
        
        return jsonify(function.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/functions/<function_id>', methods=['DELETE'])
def delete_function(function_id):
    """Delete a policy function."""
    try:
        success = policy_engine.function_manager.delete_function(function_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/functions/validate', methods=['POST'])
def validate_function():
    """Validate function code."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "Missing required field: code"}), 400
    
    result = policy_engine.validate_function_code(code)
    
    return jsonify(result)


@app.route('/api/v1/functions/test', methods=['POST'])
def test_function():
    """Test function code with the given context."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    code = data.get('code')
    context = data.get('context', {})
    
    if not code:
        return jsonify({"error": "Missing required field: code"}), 400
    
    result = policy_engine.test_function(code, context)
    
    return jsonify(result)


# Legacy API endpoints for backward compatibility

@app.route('/api/check_policy', methods=['POST'])
def legacy_check_policy():
    """Legacy endpoint for checking policies."""
    try:
        # Convert legacy format to new format if needed
        req_data = request.get_json()
        
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
            
        # Handle legacy format
        if "policy_type" not in req_data and "type" in req_data:
            req_data["policy_type"] = req_data["type"]
            
        # Route to main check_policy implementation
        return check_policy()
    except Exception as e:
        logger.exception(f"Exception in legacy_check_policy: {str(e)}")
        return jsonify({"error": f"Exception: {str(e)}"}), 500


@app.route('/api/policies', methods=['GET'])
def legacy_list_policies():
    """Legacy endpoint for listing policies."""
    policy_type = request.args.get('type')
    policies = policy_engine.list_policies(policy_type)
    return jsonify(policies)


@app.route('/api/policies', methods=['POST'])
def legacy_create_policy():
    """Legacy endpoint for creating policies."""
    return create_policy()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "version": policy_engine.policy_version if policy_engine else 0})


@app.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    """Return operational metrics for the Policy Engine."""
    if policy_engine is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
        
    try:
        # Access policy engine state
        num_policies = len(policy_engine.policies)
        num_enabled = sum(1 for p in policy_engine.policies.values() if p.get('enabled', False))
        history_count = len(policy_engine.policy_history)
        
        # Calculate hourly decision metrics
        current_time = time.time()
        one_hour_ago = current_time - 3600  # 1 hour ago
        
        # Get decisions from the last hour
        decisions_last_hour = [
            d for d in getattr(policy_engine, 'decisions_history', [])
            if d.get('timestamp', 0) >= one_hour_ago
        ]
        
        # Count allowed vs denied decisions in last hour
        allowed_last_hour = sum(1 for d in decisions_last_hour if d.get('result', False))
        denied_last_hour = sum(1 for d in decisions_last_hour if not d.get('result', False))
        
        # Calculate average decision time
        decision_times = [d.get('execution_time', 0) for d in decisions_last_hour if d.get('execution_time')]
        avg_decision_time = sum(decision_times) / len(decision_times) if decision_times else 0.0

        # Get policy application stats with fallback
        app_stats = getattr(policy_engine, 'policy_application_stats', {
            "total_checks": 0,
            "allowed_checks": 0,
            "denied_checks": 0
        })

        metrics = {
            "policy_count": num_policies,
            "enabled_policy_count": num_enabled,
            "policy_version": policy_engine.policy_version,
            "history_event_count": history_count,
            "function_count": len(policy_engine.function_manager.functions),
            "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else -1,
            # Add decision metrics for dashboard
            "policy_checks_total": app_stats.get("total_checks", 0),
            "policy_checks_allowed": app_stats.get("allowed_checks", 0),
            "policy_checks_denied": app_stats.get("denied_checks", 0),
            # Add hourly metrics for overview page
            "decisions_last_hour_total": len(decisions_last_hour),
            "decisions_last_hour_allowed": allowed_last_hour,
            "decisions_last_hour_denied": denied_last_hour,
            "avg_decision_time_ms": avg_decision_time,
            "decisions_history_count": len(getattr(policy_engine, 'decisions_history', []))
        }
        logger.debug(f"Returning metrics: {metrics}")
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        # Return basic metrics if there's an error
        return jsonify({
            "policy_count": len(policy_engine.policies) if policy_engine else 0,
            "enabled_policy_count": 0,
            "policy_version": 0,
            "history_event_count": 0,
            "function_count": 0,
            "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else -1,
            "policy_checks_total": 0,
            "policy_checks_allowed": 0,
            "policy_checks_denied": 0,
            "decisions_last_hour_total": 0,
            "decisions_last_hour_allowed": 0,
            "decisions_last_hour_denied": 0,
            "avg_decision_time_ms": 0.0,
            "decisions_history_count": 0,
            "error": str(e)
        }), 200


# Add a simple metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    """Get policy engine metrics with detailed statistics."""
    try:
        if policy_engine is None:
            return jsonify({"error": "Policy engine not initialized"}), 500
            
        # Basic metrics plus detailed application stats
        metrics_data = {
            "version": "1.0.0",
            "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else 0,
            "policy_count": len(policy_engine.policies),
            "enabled_policy_count": sum(1 for p in policy_engine.policies.values() if p.get('enabled', True)),
            "policy_version": policy_engine.policy_version,
            "policy_history_count": len(policy_engine.policy_history),
            "policy_applications_count": len(policy_engine.policy_applications),
            "policy_checks_total": policy_engine.policy_application_stats["total_checks"],
            "policy_checks_allowed": policy_engine.policy_application_stats["allowed_checks"],
            "policy_checks_denied": policy_engine.policy_application_stats["denied_checks"],
            "policy_components": list(policy_engine.policy_application_stats["by_component"].keys()),
            "policy_types": list(policy_engine.policy_application_stats["by_policy_type"].keys()),
            "policy_requesters": list(policy_engine.policy_application_stats["by_requester"].keys()),
            "latest_application_timestamp": policy_engine.policy_applications[-1]["timestamp"] if policy_engine.policy_applications else 0
        }
        
        return jsonify(metrics_data)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500


# Simple policy check endpoint
@app.route('/check', methods=['GET'])
def simple_check():
    """Simple policy check endpoint."""
    component = request.args.get('component', '')
    action = request.args.get('action', '')
    
    logger.info(f"Received policy check request for {component} to {action}")
    
    # Always allow for now
    return jsonify({
        "allowed": True,
        "reason": "Default allow policy"
    })


@app.route('/api/v1/policy_applications', methods=['GET'])
def get_policy_applications():
    """Get history of policy applications with filtering options."""
    if policy_engine is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
        
    # Get filtering parameters
    policy_type = request.args.get('policy_type')
    component = request.args.get('component')
    requester_id = request.args.get('requester_id')
    result = request.args.get('result')
    limit = request.args.get('limit', 100, type=int)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    # Convert result string to boolean if provided
    if result is not None:
        result = result.lower() == 'true' or result.lower() == 'allowed'
    
    applications = policy_engine.get_policy_applications(
        policy_type=policy_type,
        component=component,
        requester_id=requester_id,
        result=result,
        limit=limit,
        start_time=start_time,
        end_time=end_time
    )
    
    return jsonify(applications)

@app.route('/api/v1/policy_statistics', methods=['GET'])
def get_policy_statistics():
    """Get aggregated statistics about policy applications."""
    if policy_engine is None:
        return jsonify({"error": "Policy engine not initialized"}), 500
    return jsonify(policy_engine.policy_application_stats)

@app.route('/api/v1/policies/validate', methods=['POST'])
def validate_policy():
    """Validate a policy without creating it."""
    try:
        req_data = request.get_json()
        
        if not req_data:
            return jsonify({"error": "Invalid request: No JSON data"}), 400
        
        policy_data = req_data.get("policy_data") or req_data.get("data")
        if not policy_data:
            return jsonify({"error": "Missing policy_data"}), 400
        
        # Use globally defined policy_engine
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Validate the policy
        validation_result = pe.validate_policy_data(policy_data)
        
        return jsonify({
            "valid": validation_result["valid"],
            "issues": validation_result["issues"],
            "warnings": validation_result["warnings"]
        }), 200
        
    except Exception as e:
        logger.exception(f"Error validating policy: {str(e)}")
        return jsonify({"error": f"Validation error: {str(e)}"}), 500

@app.route('/api/v1/policy_decisions', methods=['GET'])
def get_policy_decisions():
    """Get policy decisions with filtering options."""
    try:
        # Get query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        policy_id = request.args.get('policy_id')
        component = request.args.get('component')
        result = request.args.get('result')
        limit = int(request.args.get('limit', 100))
        
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Get decisions history
        decisions = getattr(pe, 'decisions_history', [])
        
        # Apply filters
        if start_time:
            try:
                start_timestamp = float(start_time)
                decisions = [d for d in decisions if d.get('timestamp', 0) >= start_timestamp]
            except (ValueError, TypeError):
                pass
                
        if end_time:
            try:
                end_timestamp = float(end_time)
                decisions = [d for d in decisions if d.get('timestamp', 0) <= end_timestamp]
            except (ValueError, TypeError):
                pass
                
        if policy_id:
            decisions = [d for d in decisions if d.get('policy_id') == policy_id]
            
        if component:
            decisions = [d for d in decisions if d.get('component') == component]
            
        if result:
            result_bool = result.lower() in ['true', '1', 'allow', 'allowed']
            decisions = [d for d in decisions if d.get('result') == result_bool]
        
        # Sort by timestamp (newest first) and limit
        decisions = sorted(decisions, key=lambda x: x.get('timestamp', 0), reverse=True)[:limit]
        
        return jsonify(decisions)
        
    except Exception as e:
        logger.error(f"Error getting policy decisions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/policy_metrics', methods=['GET'])
def get_policy_metrics():
    """Get policy metrics for dashboard charts."""
    try:
        # Get query parameters
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Get policy engine instance - use global first, then Flask g
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Generate time-series metrics
        metrics = []
        current_time = time.time()
        
        # Parse time range
        if start_time and end_time:
            try:
                start_ts = float(start_time)
                end_ts = float(end_time)
            except (ValueError, TypeError):
                start_ts = current_time - 24 * 3600
                end_ts = current_time
        else:
            start_ts = current_time - 24 * 3600
            end_ts = current_time
        
        # Get actual policy applications from the policy engine
        policy_applications = getattr(pe, 'policy_applications', [])
        
        # Generate hourly metrics based on real data
        interval = 3600  # 1 hour
        timestamp = start_ts
        
        while timestamp <= end_ts:
            # Filter applications for this hour
            hour_start = timestamp
            hour_end = timestamp + interval
            
            hour_applications = [
                app for app in policy_applications
                if hour_start <= app.get('timestamp', 0) < hour_end
            ]
            
            # Calculate real metrics
            total_evaluations = len(hour_applications)
            allowed_count = sum(1 for app in hour_applications if app.get('result', False))
            denied_count = total_evaluations - allowed_count
            
            # Calculate average evaluation time
            eval_times = [app.get('evaluation_time_ms', 0) for app in hour_applications if app.get('evaluation_time_ms')]
            avg_evaluation_time = sum(eval_times) / len(eval_times) if eval_times else 0.0
            
            # Get unique requesters
            unique_requesters = len(set(app.get('requester_id', 'unknown') for app in hour_applications))
            
            # Create time-series data points for the dashboard
            hour_metrics = {
                "timestamp": timestamp,
                "iso_time": datetime.datetime.fromtimestamp(timestamp).isoformat(),
                "metric_type": "policy_count",
                "metric_name": "active_policies", 
                "metric_value": len([p for p in pe.policies.values() if p.get('enabled', True)]),
                "unit": "count"
            }
            metrics.append(hour_metrics)
            
            # Add decision count metrics
            if total_evaluations > 0:
                decision_metrics = {
                    "timestamp": timestamp,
                    "iso_time": datetime.datetime.fromtimestamp(timestamp).isoformat(),
                    "metric_type": "decision_count",
                    "metric_name": "total_decisions",
                    "metric_value": total_evaluations,
                    "allowed_count": allowed_count,
                    "denied_count": denied_count,
                    "denial_rate": round(denied_count / total_evaluations * 100, 2) if total_evaluations > 0 else 0,
                    "avg_evaluation_time_ms": round(avg_evaluation_time, 2),
                    "unique_requesters": unique_requesters,
                    "unit": "count"
                }
                metrics.append(decision_metrics)
            
            timestamp += interval
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error generating policy metrics: {e}")
        return jsonify({"error": f"Failed to generate metrics: {str(e)}"}), 500


@app.route('/api/v1/policy_version', methods=['GET'])
def get_policy_version():
    """Get current policy version for cache validation."""
    try:
        # Get policy engine instance
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        return jsonify({
            "policy_version": pe.policy_version,
            "last_updated": max([p.get("updated_at", 0) for p in pe.policies.values()] + [0]),
            "total_policies": len(pe.policies),
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting policy version: {e}")
        return jsonify({"error": f"Failed to get policy version: {str(e)}"}), 500


@app.route('/api/v1/policy_cache_check', methods=['POST'])
def check_policy_cache_validity():
    """Check if client's cached policy version is still valid."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        client_version = data.get("policy_version", 0)
        
        # Get policy engine instance
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        is_valid = client_version >= pe.policy_version
        
        response = {
            "cache_valid": is_valid,
            "current_version": pe.policy_version,
            "client_version": client_version,
            "needs_refresh": not is_valid,
            "timestamp": time.time()
        }
        
        if not is_valid:
            response["message"] = f"Client cache is outdated. Current version: {pe.policy_version}, Client version: {client_version}"
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error checking policy cache validity: {e}")
        return jsonify({"error": f"Failed to check cache validity: {str(e)}"}), 500


@app.route('/api/v1/notify_policy_update', methods=['POST'])
def notify_policy_update():
    """Notify all connected clients about policy updates (webhook-style notification)."""
    try:
        data = request.get_json()
        policy_id = data.get("policy_id") if data else None
        
        # Get policy engine instance
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Log the policy update notification
        log_event("POLICY_UPDATE_NOTIFICATION", {
            "policy_id": policy_id,
            "policy_version": pe.policy_version,
            "timestamp": time.time(),
            "notified_by": request.remote_addr
        })
        
        return jsonify({
            "success": True,
            "policy_version": pe.policy_version,
            "message": f"Policy update notification sent for policy: {policy_id}"
        })
        
    except Exception as e:
        logger.error(f"Error sending policy update notification: {e}")
        return jsonify({"error": f"Failed to send notification: {str(e)}"}), 500

@app.route('/api/v1/policy_history', methods=['GET'])
def get_policy_history():
    """
    Get policy modification history.
    
    Query parameters:
        policy_id: Filter by specific policy ID
        action: Filter by action type (create, update, delete, enable, disable)
        limit: Maximum number of history entries to return (default: 100)
        offset: Number of entries to skip (default: 0)
    """
    try:
        policy_id = request.args.get('policy_id')
        action = request.args.get('action')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Get policy engine instance
        pe = policy_engine
        if pe is None:
            pe = g.get("policy_engine")
            if pe is None:
                return jsonify({"error": "Policy engine not initialized"}), 500
        
        # Get the policy history
        history = pe.policy_history.copy()
        
        # Filter by policy_id if provided
        if policy_id:
            history = [h for h in history if h.get('policy_id') == policy_id]
        
        # Filter by action if provided
        if action:
            history = [h for h in history if h.get('action') == action]
        
        # Sort by timestamp descending (newest first)
        history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Apply pagination
        total_count = len(history)
        paginated_history = history[offset:offset + limit]
        
        # Convert timestamps to readable format and add additional info
        for entry in paginated_history:
            if 'timestamp' in entry:
                entry['timestamp_readable'] = datetime.datetime.fromtimestamp(entry['timestamp']).isoformat()
            
            # Add policy name if available
            if 'policy_id' in entry and entry['policy_id'] in pe.policies:
                policy = pe.policies[entry['policy_id']]
                entry['policy_name'] = policy.get('name', entry['policy_id'])
                entry['policy_type'] = policy.get('type', 'unknown')
        
        return jsonify({
            "history": paginated_history,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_count
        })
        
    except Exception as e:
        logger.error(f"Error getting policy history: {e}")
        return jsonify({"error": str(e)}), 500

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