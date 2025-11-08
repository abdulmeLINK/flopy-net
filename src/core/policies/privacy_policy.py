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
Privacy Policy

This module defines policies for protecting privacy in federated learning.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
import logging

from src.core.policies.policy import IPolicy, Policy

logger = logging.getLogger(__name__)


class IPrivacyPolicy(IPolicy):
    """
    Interface for privacy policies.
    
    Privacy policies define mechanisms to protect client data privacy
    in federated learning, such as differential privacy or secure aggregation.
    """
    
    @abstractmethod
    def apply_privacy_mechanism(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply privacy-preserving mechanism to data.
        
        Args:
            data: Data to be protected (model updates, gradients, etc.)
            context: Additional context for privacy mechanism
            
        Returns:
            Privacy-protected data
        """
        pass
    
    @abstractmethod
    def get_privacy_budget(self) -> Dict[str, Any]:
        """
        Get the current privacy budget status.
        
        Returns:
            Dictionary containing privacy budget information
        """
        pass


class DifferentialPrivacyPolicy(IPrivacyPolicy):
    """
    Differential Privacy policy.
    
    Implements epsilon-delta differential privacy by adding calibrated noise
    to model updates or gradients.
    """
    
    def __init__(self, policy_id: str, epsilon: float = 1.0, delta: float = 1e-5,
                noise_multiplier: float = 1.0, max_norm: Optional[float] = None,
                description: str = "Differential Privacy policy"):
        """
        Initialize the differential privacy policy.
        
        Args:
            policy_id: Unique identifier for the policy
            epsilon: Privacy parameter (smaller means more privacy)
            delta: Privacy parameter (probability of privacy breach)
            noise_multiplier: Multiplier for noise added to gradients
            max_norm: Maximum L2 norm for gradient clipping (None for no clipping)
            description: Human-readable description of the policy
        """
        self.policy_id = policy_id
        self.policy_type = "privacy"
        self.description = description
        self.epsilon = epsilon
        self.delta = delta
        self.noise_multiplier = noise_multiplier
        self.max_norm = max_norm
        self.parameters = {
            "epsilon": epsilon,
            "delta": delta,
            "noise_multiplier": noise_multiplier,
            "max_norm": max_norm
        }
        
        # Track privacy budget usage
        self.privacy_budget_used = 0.0
    
    def get_id(self) -> str:
        return self.policy_id
    
    def get_type(self) -> str:
        return self.policy_type
    
    def get_description(self) -> str:
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
                - data: Data to be protected
                
        Returns:
            Dictionary with privacy-protected data
        """
        data = context.get('data', {})
        
        protected_data = self.apply_privacy_mechanism(data, context)
        
        return {
            'protected_data': protected_data,
            'privacy_budget': self.get_privacy_budget(),
            'policy_id': self.policy_id,
            'policy_type': self.policy_type
        }
    
    def apply_privacy_mechanism(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Apply differential privacy to data.
        
        Args:
            data: Data to be protected (model updates, gradients, etc.)
            context: Additional context for privacy mechanism
            
        Returns:
            Privacy-protected data
        """
        import numpy as np
        
        # Implementation of a basic differential privacy mechanism
        # In a real implementation, use established DP libraries
        protected_data = {}
        
        for key, value in data.items():
            # Only apply to numeric data
            if isinstance(value, (int, float)):
                # Clip if max_norm is specified
                if self.max_norm is not None:
                    value = max(min(value, self.max_norm), -self.max_norm)
                
                # Add Gaussian noise
                noise = np.random.normal(0, self.noise_multiplier)
                protected_data[key] = value + noise
            
            elif hasattr(value, 'shape') and hasattr(value, '__mul__'):
                # Handle NumPy-like arrays
                array_value = np.array(value)
                
                # Clip gradient norm if max_norm is specified
                if self.max_norm is not None:
                    l2_norm = np.linalg.norm(array_value)
                    if l2_norm > self.max_norm:
                        array_value = array_value * (self.max_norm / l2_norm)
                
                # Generate noise with same shape as the array
                noise = np.random.normal(0, self.noise_multiplier, array_value.shape)
                protected_data[key] = array_value + noise
            else:
                # For non-numeric data, just pass through
                protected_data[key] = value
        
        # Update privacy budget usage (simplified calculation)
        # In a real implementation, use advanced accounting methods
        self.privacy_budget_used += self.noise_multiplier
        
        return protected_data
    
    def get_privacy_budget(self) -> Dict[str, Any]:
        """
        Get the current privacy budget status.
        
        Returns:
            Dictionary containing privacy budget information
        """
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "budget_used": self.privacy_budget_used,
            "budget_remaining": max(0, self.epsilon - self.privacy_budget_used)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy
        """
        return {
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'description': self.description,
            'parameters': self.parameters,
            'privacy_budget_used': self.privacy_budget_used
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'DifferentialPrivacyPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            DifferentialPrivacyPolicy instance
        """
        params = data.get('parameters', {})
        
        policy = DifferentialPrivacyPolicy(
            policy_id=data['policy_id'],
            epsilon=params.get('epsilon', 1.0),
            delta=params.get('delta', 1e-5),
            noise_multiplier=params.get('noise_multiplier', 1.0),
            max_norm=params.get('max_norm', None),
            description=data.get('description', "Differential Privacy policy")
        )
        
        if 'privacy_budget_used' in data:
            policy.privacy_budget_used = data['privacy_budget_used']
            
        return policy


class PrivacyPolicy(Policy):
    """
    Privacy policy for federated learning.
    
    This policy focuses on privacy protection mechanisms like differential privacy
    and secure aggregation.
    """
    
    def __init__(
        self,
        policy_id: str = None,
        name: str = "Privacy Policy",
        description: str = "Policy for privacy protection in federated learning",
        rules: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a privacy policy.
        
        Args:
            policy_id: Unique identifier for the policy
            name: Human-readable name for the policy
            description: Description of the policy's purpose
            rules: Policy rules
            metadata: Additional metadata for the policy
        """
        if rules is None:
            rules = self._get_default_privacy_rules()
        
        if metadata is None:
            metadata = {}
        
        # Add privacy-specific metadata
        metadata["type"] = "privacy"
        metadata["privacy_budget"] = rules.get("differential_privacy", {}).get("epsilon", 1.0)
        
        super().__init__(policy_id, name, description, rules, metadata)
    
    def _get_default_privacy_rules(self) -> Dict[str, Any]:
        """
        Get default rules for privacy protection.
        
        Returns:
            Default privacy policy rules
        """
        return {
            "differential_privacy": {
                "enabled": True,
                "epsilon": 1.0,
                "delta": 1e-5,
                "clip_norm": 1.0,
                "noise_multiplier": 0.1
            },
            "secure_aggregation": {
                "enabled": True,
                "min_clients": 3,
                "threshold": 2,
                "encryption_type": "homomorphic"
            },
            "data_minimization": {
                "enabled": True,
                "pii_removal": True,
                "feature_reduction": False
            }
        }
    
    def _evaluate_rule(
        self, rule_id: str, rule: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single rule.
        
        Args:
            rule_id: ID of the rule being evaluated
            rule: Rule definition
            context: Contextual information for rule evaluation
            
        Returns:
            Rule evaluation result
        """
        result = {
            "applied": True,
            "violations": [],
            "recommendations": []
        }
        
        # Evaluate differential privacy rule
        if rule_id == "differential_privacy" and rule.get("enabled", False):
            # Check if differential privacy is applied
            dp_applied = context.get("differential_privacy_applied", False)
            dp_epsilon = context.get("epsilon", float("inf"))
            dp_delta = context.get("delta", 1.0)
            
            # Violations
            if not dp_applied:
                result["violations"].append("Differential privacy not applied")
                result["recommendations"].append(
                    f"Apply differential privacy with epsilon={rule['epsilon']}"
                )
            elif dp_epsilon > rule["epsilon"]:
                result["violations"].append(
                    f"Epsilon value too high: {dp_epsilon} > {rule['epsilon']}"
                )
                result["recommendations"].append(
                    f"Reduce epsilon value to at most {rule['epsilon']}"
                )
            elif dp_delta > rule["delta"]:
                result["violations"].append(
                    f"Delta value too high: {dp_delta} > {rule['delta']}"
                )
                result["recommendations"].append(
                    f"Reduce delta value to at most {rule['delta']}"
                )
        
        # Evaluate secure aggregation rule
        elif rule_id == "secure_aggregation" and rule.get("enabled", False):
            # Check if secure aggregation is applied
            sa_applied = context.get("secure_aggregation_applied", False)
            sa_min_clients = context.get("min_clients", 0)
            
            # Violations
            if not sa_applied:
                result["violations"].append("Secure aggregation not applied")
                result["recommendations"].append(
                    "Enable secure aggregation for model updates"
                )
            elif sa_min_clients < rule.get("min_clients", 3):
                result["violations"].append(
                    f"Minimum clients too low: {sa_min_clients} < {rule['min_clients']}"
                )
                result["recommendations"].append(
                    f"Increase minimum clients to at least {rule['min_clients']}"
                )
        
        # Evaluate data minimization rule
        elif rule_id == "data_minimization" and rule.get("enabled", False):
            # Check if data minimization is applied
            dm_applied = context.get("data_minimization_applied", False)
            pii_removed = context.get("pii_removed", False)
            
            # Violations
            if not dm_applied:
                result["violations"].append("Data minimization not applied")
                result["recommendations"].append(
                    "Apply data minimization techniques"
                )
            elif rule.get("pii_removal", False) and not pii_removed:
                result["violations"].append("PII not removed from data")
                result["recommendations"].append(
                    "Remove personally identifiable information from data"
                )
        
        return result
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the privacy policy against the given context.
        
        Args:
            context: Contextual information for policy evaluation
            
        Returns:
            Evaluation result
        """
        # First get the base evaluation
        result = super().evaluate(context)
        
        # Add privacy-specific metrics
        privacy_budget_consumed = context.get("privacy_budget_consumed", 0.0)
        budget_remaining = self.metadata.get("privacy_budget", 1.0) - privacy_budget_consumed
        
        result["privacy_metrics"] = {
            "privacy_budget_consumed": privacy_budget_consumed,
            "privacy_budget_remaining": max(0.0, budget_remaining),
            "epsilon": context.get("epsilon", None),
            "delta": context.get("delta", None)
        }
        
        return result 