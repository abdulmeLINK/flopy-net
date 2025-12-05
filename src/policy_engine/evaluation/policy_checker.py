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
Policy Checker Module.

This module provides the PolicyChecker class for evaluating policies against contexts.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from src.policy_engine.evaluation.condition_evaluator import ConditionEvaluator
from src.policy_engine.evaluation.application_tracker import ApplicationTracker
from src.policy_engine.policy_functions import PolicyFunction, PolicyFunctionError

logger = logging.getLogger(__name__)


class PolicyChecker:
    """Checks policies against contexts and tracks results."""
    
    # Action categories for rule processing
    DENY_ACTIONS = ["deny", "block", "reject", "forbid", "quarantine", "isolate", "suspend"]
    CONFIGURE_ACTIONS = ["configure", "modify", "adjust", "tune", "set"]
    ALLOW_ACTIONS = ["allow", "permit", "grant", "authorize"]
    LOG_ACTIONS = ["log", "audit", "record", "track"]
    MONITOR_ACTIONS = ["monitor", "watch", "observe", "inspect"]
    THROTTLE_ACTIONS = ["throttle", "limit", "restrict"]
    PRIORITY_ACTIONS = ["prioritize", "boost", "elevate"]
    FILTER_ACTIONS = ["filter", "select", "choose"]
    ENFORCE_ACTIONS = ["enforce", "apply", "implement"]
    VERIFY_ACTIONS = ["verify", "validate", "check", "confirm"]
    RETRY_ACTIONS = ["retry", "repeat", "reattempt"]
    CHECKPOINT_ACTIONS = ["checkpoint", "save", "backup"]
    FAILOVER_ACTIONS = ["failover", "fallback", "redirect"]
    SIMULATE_ACTIONS = ["simulate", "test", "mock"]
    TRAFFIC_ACTIONS = ["rate_limit", "distribute", "reroute", "scale"]
    
    def __init__(self, condition_evaluator: ConditionEvaluator, 
                 application_tracker: ApplicationTracker,
                 function_manager: Optional[Any] = None):
        """
        Initialize the policy checker.
        
        Args:
            condition_evaluator: ConditionEvaluator instance for evaluating conditions
            application_tracker: ApplicationTracker instance for tracking applications
            function_manager: Optional PolicyFunctionManager for function-based policies
        """
        self.condition_evaluator = condition_evaluator
        self.application_tracker = application_tracker
        self.function_manager = function_manager
    
    def check_policy(self, policy_type: str, context: Dict[str, Any], 
                     policies: Dict[str, Dict[str, Any]], 
                     log_event_callback=None,
                     log_decision_callback=None) -> Dict[str, Any]:
        """
        Check if an operation is allowed by the policies with enhanced decision tracking.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            policies: Dictionary of policies to check against
            log_event_callback: Optional callback for logging events
            log_decision_callback: Optional callback for logging decisions
            
        Returns:
            Dictionary with comprehensive policy decision and detailed metadata
        """
        start_time = time.time()
        
        # Extract context information
        requester_id = context.get("requester_id", "unknown")
        component = context.get("component", "unknown")
        
        # Get matching policies
        matching_policies = [p for p in policies.values() if p.get("type") == policy_type]
        
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
            self.application_tracker.record_policy_application(
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
            if log_event_callback:
                log_event_callback("POLICY_EVAL_RESULT", {
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
            if "function_id" in policy_data and self.function_manager:
                policy_evaluation, violations, applied_actions, decision_path, total_rules_evaluated, matched_rules_count = \
                    self._evaluate_function_policy(
                        policy_data, policy_id, policy_name, context,
                        policy_evaluation, violations, applied_actions, 
                        decision_path, total_rules_evaluated, matched_rules_count
                    )
                    
            # Check if the policy has a function code embedded
            elif "function_code" in policy_data:
                policy_evaluation, violations, applied_actions, decision_path, total_rules_evaluated, matched_rules_count = \
                    self._evaluate_embedded_function_policy(
                        policy_data, policy_id, policy_name, context,
                        policy_evaluation, violations, applied_actions,
                        decision_path, total_rules_evaluated, matched_rules_count
                    )
                    
            # Otherwise, check using the policy data directly
            else:
                policy_evaluation, violations, applied_actions, decision_path, \
                total_rules_evaluated, matched_rules_count, collected_parameters = \
                    self._evaluate_rule_based_policy(
                        policy_data, policy_id, policy_name, context,
                        policy_evaluation, violations, applied_actions,
                        decision_path, total_rules_evaluated, matched_rules_count,
                        collected_parameters
                    )
            
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
            configure_actions = [a for a in applied_actions if a["action"] in self.CONFIGURE_ACTIONS]
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
        self.application_tracker.record_policy_application(
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
        if log_decision_callback:
            for policy_evaluation in rule_evaluations:
                decision_data = {
                    "allowed": allowed,
                    "action": "allow" if allowed else "deny",
                    "reason": primary_reason,
                    "rule_evaluations": policy_evaluation["rules_evaluated"],
                    "matched_rules": policy_evaluation["matched_rules"],
                    "actions_applied": policy_evaluation["actions_applied"]
                }
                log_decision_callback(policy_evaluation["policy_id"], context, decision_data, policy_evaluation["evaluation_time_ms"])

        # Log policy evaluation result
        if log_event_callback:
            log_event_callback("POLICY_EVAL_RESULT", {
                "request_id": context.get("request_id", f"req_{int(time.time())}"),
                "policy_type": policy_type,
                "result": result,
                "elapsed_ms": (time.time() - start_time) * 1000
            })
        
        return result
    
    def _evaluate_function_policy(self, policy_data, policy_id, policy_name, context,
                                   policy_evaluation, violations, applied_actions,
                                   decision_path, total_rules_evaluated, matched_rules_count):
        """Evaluate a function-based policy."""
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
                "function_id": policy_data.get("function_id")
            }
            violations.append(violation)
            decision_path.append(f"policy:{policy_id}:function_error")
        
        return policy_evaluation, violations, applied_actions, decision_path, total_rules_evaluated, matched_rules_count
    
    def _evaluate_embedded_function_policy(self, policy_data, policy_id, policy_name, context,
                                            policy_evaluation, violations, applied_actions,
                                            decision_path, total_rules_evaluated, matched_rules_count):
        """Evaluate an embedded function policy."""
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
        
        return policy_evaluation, violations, applied_actions, decision_path, total_rules_evaluated, matched_rules_count
    
    def _evaluate_rule_based_policy(self, policy_data, policy_id, policy_name, context,
                                     policy_evaluation, violations, applied_actions,
                                     decision_path, total_rules_evaluated, matched_rules_count,
                                     collected_parameters):
        """Evaluate a rule-based policy."""
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
                    condition_matched, condition_reason = self.condition_evaluator.evaluate_condition(value, context, rule_parameters)
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
                
                # Process the action
                action_result = self._process_action(
                    action, policy_id, policy_name, rule_index,
                    rule_description, rule_parameters, match_details,
                    violations, applied_actions, policy_evaluation, collected_parameters
                )
                violations, applied_actions, policy_evaluation, collected_parameters = action_result
        
        return policy_evaluation, violations, applied_actions, decision_path, \
               total_rules_evaluated, matched_rules_count, collected_parameters
    
    def _process_action(self, action, policy_id, policy_name, rule_index,
                        rule_description, rule_parameters, match_details,
                        violations, applied_actions, policy_evaluation, collected_parameters):
        """Process a policy action."""
        action_entry = {
            "action": action,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "rule_index": rule_index,
            "reason": rule_description,
            "parameters": rule_parameters,
            "match_details": match_details
        }
        
        if action in self.DENY_ACTIONS:
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
            applied_actions.append(action_entry)
            policy_evaluation["result"] = action
            
        elif action in self.CONFIGURE_ACTIONS:
            logger.debug(f"Policy {policy_id} rule {rule_index} matched configure rule. Parameters: {rule_parameters}")
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.ALLOW_ACTIONS:
            applied_actions.append(action_entry)
            
        elif action in self.LOG_ACTIONS:
            logger.info(f"Policy {policy_id} rule {rule_index}: {rule_description}")
            applied_actions.append(action_entry)
            
        elif action in self.MONITOR_ACTIONS:
            applied_actions.append(action_entry)
            
        elif action in self.THROTTLE_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.PRIORITY_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.FILTER_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.ENFORCE_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.VERIFY_ACTIONS:
            applied_actions.append(action_entry)
            
        elif action in self.RETRY_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.CHECKPOINT_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.FAILOVER_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        elif action in self.SIMULATE_ACTIONS:
            applied_actions.append(action_entry)
            
        elif action in self.TRAFFIC_ACTIONS:
            collected_parameters.update(rule_parameters)
            applied_actions.append(action_entry)
            
        else:
            # Unknown action - treat as informational
            logger.warning(f"Unknown action '{action}' in policy {policy_id} rule {rule_index}")
            action_entry["reason"] = f"Unknown action: {rule_description}"
            applied_actions.append(action_entry)
        
        return violations, applied_actions, policy_evaluation, collected_parameters
