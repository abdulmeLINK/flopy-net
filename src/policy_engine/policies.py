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
Policy Management Module

This module provides classes for managing and evaluating policies.
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Callable

logger = logging.getLogger(__name__)

class PolicyEvaluationError(Exception):
    """Exception raised for errors during policy evaluation."""
    pass

class Policy:
    """
    Represents a policy with evaluation logic.
    """
    
    def __init__(self, policy_id: str, policy_data: Dict[str, Any]):
        """
        Initialize a policy object.
        
        Args:
            policy_id: Unique identifier for the policy
            policy_data: Policy configuration data
        """
        self.id = policy_id
        self.data = policy_data
        self.name = policy_data.get('name', f'Policy-{policy_id}')
        self.description = policy_data.get('description', '')
        self.effect = policy_data.get('effect', 'deny').lower()
        self.conditions = policy_data.get('conditions', [])
        self.enabled = policy_data.get('enabled', True)
        self.created_at = policy_data.get('created_at', time.time())
        self.updated_at = policy_data.get('updated_at', time.time())
        
        logger.debug(f"Initialized policy {self.id}: {self.name}")
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy against the given context.
        
        Args:
            context: Contextual data for policy evaluation
            
        Returns:
            Dictionary with evaluation results
        """
        if not self.enabled:
            return {
                'allowed': True if self.effect == 'deny' else False,
                'reason': 'Policy is disabled',
                'policy_id': self.id
            }
        
        try:
            # Default to allowing or denying based on effect
            result = (self.effect == 'allow')
            reason = f"Default {self.effect} policy"
            violations = []
            
            # Check all conditions
            if self.conditions:
                for condition in self.conditions:
                    condition_type = condition.get('type', 'unknown')
                    condition_data = condition.get('data', {})
                    
                    # Evaluate condition (simplified)
                    condition_result = self._evaluate_condition(condition_type, condition_data, context)
                    condition_passed = condition_result.get('passed', False)
                    
                    # For 'allow' policy, all conditions must pass
                    # For 'deny' policy, any failing condition triggers denial
                    if self.effect == 'allow' and not condition_passed:
                        result = False
                        reason = condition_result.get('reason', f"Condition {condition_type} failed")
                        violations.append({
                            'condition': condition_type,
                            'reason': reason
                        })
                        break
                    elif self.effect == 'deny' and not condition_passed:
                        result = False
                        reason = condition_result.get('reason', f"Condition {condition_type} failed")
                        violations.append({
                            'condition': condition_type,
                            'reason': reason
                        })
                        break
            
            return {
                'allowed': result,
                'reason': reason,
                'policy_id': self.id,
                'violations': violations
            }
            
        except Exception as e:
            logger.error(f"Error evaluating policy {self.id}: {str(e)}")
            raise PolicyEvaluationError(f"Error evaluating policy {self.id}: {str(e)}")
    
    def _evaluate_condition(self, condition_type: str, condition_data: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a policy condition.
        
        Args:
            condition_type: Type of condition
            condition_data: Condition configuration
            context: Evaluation context
            
        Returns:
            Dictionary with evaluation results
        """
        # Simple example implementation - for demonstration only
        if condition_type == 'attribute_match':
            attribute = condition_data.get('attribute', '')
            expected_value = condition_data.get('value', None)
            
            if attribute in context:
                actual_value = context[attribute]
                if actual_value == expected_value:
                    return {'passed': True, 'reason': f"Attribute {attribute} matched expected value"}
                else:
                    return {'passed': False, 'reason': f"Attribute {attribute} value mismatch"}
            else:
                return {'passed': False, 'reason': f"Attribute {attribute} not found in context"}
                
        # Default pass for unknown condition types
        return {'passed': True, 'reason': 'Unknown condition type, defaulting to pass'}


class PolicyManager:
    """
    Manages a collection of policies.
    """
    
    def __init__(self, policy_file: Optional[str] = None):
        """
        Initialize the policy manager.
        
        Args:
            policy_file: Path to the JSON policy file
        """
        self.policies: Dict[str, Policy] = {}
        self.policy_file = policy_file
        self.default_policy_id = None
        
        # Load policies if file is provided
        if policy_file:
            self.load_policies(policy_file)
        
        logger.info(f"Initialized PolicyManager with {len(self.policies)} policies")
    
    def load_policies(self, policy_file: Optional[str] = None) -> bool:
        """
        Load policies from a JSON file.
        
        Args:
            policy_file: Path to the JSON policy file
            
        Returns:
            True if policies were loaded successfully, False otherwise
        """
        file_path = policy_file or self.policy_file
        if not file_path:
            logger.warning("No policy file specified")
            return False
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Clear existing policies
                self.policies = {}
                
                # Load policies from file
                if 'policies' in data:
                    for policy_data in data['policies']:
                        policy_id = policy_data.get('id', '')
                        if policy_id:
                            self.policies[policy_id] = Policy(policy_id, policy_data)
                
                # Set default policy
                self.default_policy_id = data.get('default_policy')
                
                logger.info(f"Loaded {len(self.policies)} policies from {file_path}")
                return True
            else:
                logger.warning(f"Policy file not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading policies: {str(e)}")
            return False
    
    def save_policies(self, policy_file: Optional[str] = None) -> bool:
        """
        Save policies to a JSON file.
        
        Args:
            policy_file: Path to the JSON policy file
            
        Returns:
            True if policies were saved successfully, False otherwise
        """
        file_path = policy_file or self.policy_file
        if not file_path:
            logger.warning("No policy file specified")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Build policy data
            policies_data = []
            for policy_id, policy in self.policies.items():
                policy_data = {
                    'id': policy.id,
                    'name': policy.name,
                    'description': policy.description,
                    'effect': policy.effect,
                    'conditions': policy.conditions,
                    'enabled': policy.enabled,
                    'created_at': policy.created_at,
                    'updated_at': policy.updated_at
                }
                policies_data.append(policy_data)
            
            # Create JSON data
            data = {
                'policies': policies_data,
                'default_policy': self.default_policy_id
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.policies)} policies to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving policies: {str(e)}")
            return False
    
    def add_policy(self, policy_data: Dict[str, Any]) -> Optional[str]:
        """
        Add a new policy.
        
        Args:
            policy_data: Policy configuration
            
        Returns:
            Policy ID if successful, None otherwise
        """
        policy_id = policy_data.get('id')
        
        # Generate ID if not provided
        if not policy_id:
            import uuid
            policy_id = str(uuid.uuid4())
            policy_data['id'] = policy_id
        
        # Add creation timestamp if not present
        if 'created_at' not in policy_data:
            policy_data['created_at'] = time.time()
        
        # Add update timestamp
        policy_data['updated_at'] = time.time()
        
        # Create policy
        try:
            self.policies[policy_id] = Policy(policy_id, policy_data)
            logger.info(f"Added policy {policy_id}: {policy_data.get('name', 'Unnamed policy')}")
            return policy_id
        except Exception as e:
            logger.error(f"Error adding policy: {str(e)}")
            return None
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """
        Get a policy by ID.
        
        Args:
            policy_id: Policy ID
            
        Returns:
            Policy if found, None otherwise
        """
        return self.policies.get(policy_id)
    
    def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> bool:
        """
        Update an existing policy.
        
        Args:
            policy_id: Policy ID
            policy_data: Updated policy configuration
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.warning(f"Policy {policy_id} not found")
            return False
        
        try:
            # Keep creation timestamp
            if 'created_at' not in policy_data and hasattr(self.policies[policy_id], 'created_at'):
                policy_data['created_at'] = self.policies[policy_id].created_at
            
            # Update timestamp
            policy_data['updated_at'] = time.time()
            
            # Update policy
            self.policies[policy_id] = Policy(policy_id, policy_data)
            logger.info(f"Updated policy {policy_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating policy {policy_id}: {str(e)}")
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """
        Delete a policy.
        
        Args:
            policy_id: Policy ID
            
        Returns:
            True if successful, False otherwise
        """
        if policy_id not in self.policies:
            logger.warning(f"Policy {policy_id} not found")
            return False
        
        try:
            del self.policies[policy_id]
            
            # Reset default policy if it was the deleted one
            if self.default_policy_id == policy_id:
                self.default_policy_id = None
            
            logger.info(f"Deleted policy {policy_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting policy {policy_id}: {str(e)}")
            return False
    
    def evaluate_all(self, context: Dict[str, Any], policy_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate all applicable policies.
        
        Args:
            context: Evaluation context
            policy_type: Optional policy type filter
            
        Returns:
            Evaluation results
        """
        results = []
        allowed = True
        final_reason = "All policies passed"
        
        try:
            # Filter policies by type if specified
            applicable_policies = {}
            for policy_id, policy in self.policies.items():
                if policy.enabled and (not policy_type or policy.data.get('type') == policy_type):
                    applicable_policies[policy_id] = policy
            
            # If no applicable policies, check default
            if not applicable_policies and self.default_policy_id in self.policies:
                default_policy = self.policies[self.default_policy_id]
                result = default_policy.evaluate(context)
                results.append({
                    'policy_id': default_policy.id,
                    'name': default_policy.name,
                    'allowed': result['allowed'],
                    'reason': result['reason']
                })
                
                allowed = result['allowed']
                final_reason = f"Default policy ({default_policy.name}): {result['reason']}"
            else:
                # Evaluate all applicable policies
                for policy_id, policy in applicable_policies.items():
                    result = policy.evaluate(context)
                    results.append({
                        'policy_id': policy.id,
                        'name': policy.name,
                        'allowed': result['allowed'],
                        'reason': result['reason']
                    })
                    
                    # For deny effect policies, any denial is final
                    if not result['allowed']:
                        allowed = False
                        final_reason = f"Policy {policy.name}: {result['reason']}"
                        break
            
            return {
                'allowed': allowed,
                'reason': final_reason,
                'results': results
            }
        except Exception as e:
            logger.error(f"Error evaluating policies: {str(e)}")
            return {
                'allowed': False,
                'reason': f"Error evaluating policies: {str(e)}",
                'results': results
            } 