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
Policy Interface

This module defines the base interface for all policies in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class IPolicy(ABC):
    """
    Base interface for all policies in the system.
    
    Policies define rules that govern the behavior of different components
    in the federated learning system.
    """
    
    @abstractmethod
    def get_id(self) -> str:
        """
        Get the policy ID.
        
        Returns:
            Policy ID
        """
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """
        Get the policy type.
        
        Returns:
            Policy type
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get the policy description.
        
        Returns:
            Policy description
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the policy parameters.
        
        Returns:
            Dictionary of policy parameters
        """
        pass
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
            
        Returns:
            Evaluation result
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy
        """
        pass
    
    @staticmethod
    @abstractmethod
    def from_dict(data: Dict[str, Any]) -> 'IPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            Policy instance
        """
        pass

class Policy(IPolicy):
    """
    Base Policy class for federated learning.
    
    This class provides the basic functionality for policies used in federated learning,
    including rule management and evaluation.
    """
    
    def __init__(
        self,
        policy_id: str = None,
        policy_type: str = "generic",
        name: str = "Base Policy",
        description: str = "Base policy for federated learning",
        rules: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a policy.
        
        Args:
            policy_id: Unique identifier for the policy
            policy_type: Type of policy (e.g., "network_security", "client_selection")
            name: Human-readable name for the policy
            description: Description of the policy's purpose
            rules: Policy rules
            parameters: Policy configuration parameters
            metadata: Additional metadata for the policy
        """
        self.policy_id = policy_id or f"policy-{uuid.uuid4()}"
        self.policy_type = policy_type
        self.name = name
        self.description = description
        self.rules = rules or []
        self.parameters = parameters or {}
        self.metadata = metadata or {}
        
        logger.info(f"Initialized policy {self.policy_id} ({self.name}) of type {self.policy_type}")
    
    def get_id(self) -> str:
        """
        Get the policy ID.
        
        Returns:
            Policy ID
        """
        return self.policy_id
    
    def get_type(self) -> str:
        """
        Get the policy type.
        
        Returns:
            Policy type
        """
        return self.policy_type
    
    def get_description(self) -> str:
        """
        Get the policy description.
        
        Returns:
            Policy description
        """
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get the policy parameters.
        
        Returns:
            Dictionary of policy parameters
        """
        return self.parameters
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """
        Add a rule to the policy.
        
        Args:
            rule: Rule definition
        """
        self.rules.append(rule)
        logger.info(f"Added rule to policy {self.policy_id}")
    
    def remove_rule(self, rule_index: int) -> bool:
        """
        Remove a rule from the policy.
        
        Args:
            rule_index: Index of the rule to remove
            
        Returns:
            True if the rule was removed, False otherwise
        """
        if 0 <= rule_index < len(self.rules):
            del self.rules[rule_index]
            logger.info(f"Removed rule {rule_index} from policy {self.policy_id}")
            return True
        
        logger.warning(f"Rule index {rule_index} out of range for policy {self.policy_id}")
        return False
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
            
        Returns:
            Evaluation result
        """
        violations = []
        applied_rules = []
        
        # Check each rule
        for i, rule in enumerate(self.rules):
            rule_type = rule.get("type", "unknown")
            condition = rule.get("condition", {})
            
            # Check if the rule applies to this context
            if self._check_condition(condition, context):
                applied_rules.append(i)
                
                # Check if the rule is violated
                if not self._check_compliance(rule, context):
                    violations.append({
                        "rule_index": i,
                        "rule_type": rule_type,
                        "message": rule.get("message", f"Violated {rule_type} rule")
                    })
        
        # Build recommendations if there are violations
        recommendations = []
        if violations:
            for violation in violations:
                rule_index = violation.get("rule_index")
                if rule_index is not None and rule_index < len(self.rules):
                    rule = self.rules[rule_index]
                    if "recommendation" in rule:
                        recommendations.append(rule["recommendation"])
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "recommendations": recommendations,
            "applied_rules": applied_rules
        }
    
    def _check_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a condition applies to a context.
        
        Args:
            condition: Condition to check
            context: Context to check against
            
        Returns:
            True if the condition applies, False otherwise
        """
        # If no condition is specified, the rule always applies
        if not condition:
            return True
        
        operator = condition.get("operator", "AND")
        predicates = condition.get("predicates", [])
        
        if not predicates:
            return True
        
        results = []
        for predicate in predicates:
            param = predicate.get("param")
            value = predicate.get("value")
            comparison = predicate.get("comparison", "eq")
            
            if param not in context:
                results.append(False)
                continue
            
            context_value = context[param]
            
            if comparison == "eq":
                results.append(context_value == value)
            elif comparison == "ne":
                results.append(context_value != value)
            elif comparison == "gt":
                results.append(context_value > value)
            elif comparison == "lt":
                results.append(context_value < value)
            elif comparison == "gte":
                results.append(context_value >= value)
            elif comparison == "lte":
                results.append(context_value <= value)
            elif comparison == "in":
                results.append(context_value in value)
            elif comparison == "not_in":
                results.append(context_value not in value)
            else:
                results.append(False)
        
        if operator == "AND":
            return all(results)
        elif operator == "OR":
            return any(results)
        else:
            return False
    
    def _check_compliance(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a context complies with a rule.
        
        Args:
            rule: Rule to check
            context: Context to check
            
        Returns:
            True if compliant, False otherwise
        """
        rule_type = rule.get("type", "unknown")
        
        # Handle different rule types
        if rule_type == "network_security":
            return self._check_security_rule(rule, context)
        elif rule_type == "network_qos":
            return self._check_qos_rule(rule, context)
        elif rule_type == "client_selection":
            return self._check_client_selection_rule(rule, context)
        elif rule_type == "privacy":
            return self._check_privacy_rule(rule, context)
        else:
            # For generic rules, check the requirement
            requirement = rule.get("requirement", {})
            return self._check_condition(requirement, context)
    
    def _check_security_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a context complies with a security rule.
        
        Args:
            rule: Security rule to check
            context: Context to check
            
        Returns:
            True if compliant, False otherwise
        """
        requirement = rule.get("requirement", {})
        
        # Extract relevant fields from context
        src_ip = context.get("src_ip")
        dst_ip = context.get("dst_ip")
        protocol = context.get("protocol")
        port = context.get("port")
        
        # Check blocked IPs
        blocked_ips = requirement.get("blocked_ips", [])
        if src_ip in blocked_ips or dst_ip in blocked_ips:
            return False
        
        # Check allowed IPs
        allowed_ips = requirement.get("allowed_ips", [])
        if allowed_ips and (src_ip not in allowed_ips and dst_ip not in allowed_ips):
            return False
        
        # Check blocked ports
        blocked_ports = requirement.get("blocked_ports", [])
        if port in blocked_ports:
            return False
        
        # Check encryption requirement
        required_encryption = requirement.get("required_encryption")
        if required_encryption:
            encryption = context.get("encryption", {})
            if not encryption:
                return False
            
            enc_type = encryption.get("type")
            enc_strength = encryption.get("strength", 0)
            
            if (required_encryption.get("type") and enc_type != required_encryption.get("type")) or \
               (required_encryption.get("strength", 0) > enc_strength):
                return False
        
        return True
    
    def _check_qos_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a context complies with a QoS rule.
        
        Args:
            rule: QoS rule to check
            context: Context to check
            
        Returns:
            True if compliant, False otherwise
        """
        requirement = rule.get("requirement", {})
        
        # Extract relevant fields from context
        bandwidth = context.get("bandwidth", 0)
        latency = context.get("latency", 0)
        traffic_class = context.get("traffic_class", "default")
        
        # Check bandwidth requirement
        min_bandwidth = requirement.get("min_bandwidth", 0)
        if bandwidth < min_bandwidth:
            return False
        
        # Check latency requirement
        max_latency = requirement.get("max_latency", float("inf"))
        if latency > max_latency:
            return False
        
        # Check traffic class
        allowed_traffic_classes = requirement.get("allowed_traffic_classes", ["default"])
        if traffic_class not in allowed_traffic_classes:
            return False
        
        return True
    
    def _check_client_selection_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a context complies with a client selection rule.
        
        Args:
            rule: Client selection rule to check
            context: Context to check
            
        Returns:
            True if compliant, False otherwise
        """
        requirement = rule.get("requirement", {})
        
        # Extract relevant fields from context
        client_id = context.get("client_id")
        client_resources = context.get("resources", {})
        
        # Check allowed clients
        allowed_clients = requirement.get("allowed_clients", [])
        if allowed_clients and client_id not in allowed_clients:
            return False
        
        # Check minimum resource requirements
        min_resources = requirement.get("min_resources", {})
        for resource, min_value in min_resources.items():
            if resource not in client_resources or client_resources[resource] < min_value:
                return False
        
        return True
    
    def _check_privacy_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a context complies with a privacy rule.
        
        Args:
            rule: Privacy rule to check
            context: Context to check
            
        Returns:
            True if compliant, False otherwise
        """
        requirement = rule.get("requirement", {})
        
        # Extract relevant fields from context
        privacy_methods = context.get("privacy_methods", [])
        
        # Check required privacy methods
        required_methods = requirement.get("required_methods", [])
        for method in required_methods:
            if method not in privacy_methods:
                return False
        
        # Check differential privacy parameters
        if "differential_privacy" in requirement:
            dp_context = next((m for m in privacy_methods if m.get("type") == "differential_privacy"), None)
            if not dp_context:
                return False
            
            dp_req = requirement["differential_privacy"]
            epsilon = dp_context.get("epsilon", float("inf"))
            delta = dp_context.get("delta", 1.0)
            
            if epsilon > dp_req.get("max_epsilon", float("inf")) or delta > dp_req.get("max_delta", 1.0):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary representation.
        
        Returns:
            Dictionary representation of the policy
        """
        return {
            "policy_id": self.policy_id,
            "policy_type": self.policy_type,
            "name": self.name,
            "description": self.description,
            "rules": self.rules,
            "parameters": self.parameters,
            "metadata": self.metadata
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Policy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            Policy instance
        """
        return Policy(
            policy_id=data.get("policy_id"),
            policy_type=data.get("policy_type", "generic"),
            name=data.get("name", "Unnamed Policy"),
            description=data.get("description", ""),
            rules=data.get("rules", []),
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        ) 