"""
Basic policies for federated learning.
Implements standard federated learning policy for basic scenarios.
"""

from typing import Dict, List, Any, Optional
import logging

from src.core.policies.policy import Policy

logger = logging.getLogger(__name__)


class BasicPolicy(Policy):
    """
    Policy for basic applications in federated learning.
    Focuses on standard federated learning requirements.
    """

    def __init__(
        self,
        policy_id: str,
        name: str = "Basic Policy",
        description: str = "Standard federated learning policy",
        rules: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a basic policy.

        Args:
            policy_id: Unique identifier for the policy
            name: Human-readable name for the policy
            description: Description of the policy's purpose
            rules: Policy rules
            metadata: Additional metadata
        """
        if rules is None:
            rules = self._get_default_basic_rules()
        
        if metadata is None:
            metadata = {}
        
        # Add basic-specific metadata
        metadata["domain"] = "basic"
        metadata["sensitivity"] = "low"
        
        super().__init__(policy_id, name, description, rules, metadata)
    
    def _get_default_basic_rules(self) -> Dict[str, Any]:
        """
        Get default rules for basic applications.
        
        Returns:
            Default basic policy rules
        """
        return {
            "differential_privacy": {
                "enabled": False,
                "noise_scale": 0.1,
                "clip_norm": 1.0
            },
            "secure_aggregation": {
                "enabled": True,
                "min_clients": 1,
                "encryption_type": "simple"
            },
            "data_retention": {
                "enabled": False,
                "max_days": 90,
                "require_consent": False
            },
            "client_selection": {
                "min_data_samples": 10,
                "certification_required": False,
                "geographical_restrictions": []
            },
            "model_evaluation": {
                "metrics": ["accuracy", "loss"],
                "privacy_budget": 10.0
            }
        }
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy against the given context.
        
        Args:
            context: Contextual information for policy evaluation
            
        Returns:
            Evaluation result with recommendations
        """
        result = {
            "compliant": True,
            "recommendations": [],
            "violations": [],
            "applied_rules": []
        }
        
        # Check for secure aggregation
        if "aggregation" in context and "secure_aggregation" in self.rules:
            sa_rule = self.rules["secure_aggregation"]
            if sa_rule["enabled"]:
                result["applied_rules"].append("secure_aggregation")
                
                # Check if minimum client count is met
                client_count = context.get("client_count", 0)
                if client_count < sa_rule["min_clients"]:
                    result["compliant"] = False
                    result["violations"].append(
                        "Insufficient clients for secure aggregation. Required: {}, Found: {}".format(
                            sa_rule["min_clients"], client_count
                        )
                    )
        
        # Apply additional policy evaluations
        self._evaluate_client_selection(context, result)
        
        return result
    
    def _evaluate_client_selection(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Evaluate client selection rules.
        
        Args:
            context: Contextual information for policy evaluation
            result: Evaluation result to update
        """
        if "client_selection" in self.rules and "client" in context:
            selection_rule = self.rules["client_selection"]
            client = context.get("client", {})
            
            # Check data sample count
            if client.get("data_samples", 0) < selection_rule["min_data_samples"]:
                result["compliant"] = False
                result["violations"].append(
                    "Insufficient data samples. Required: {}, Found: {}".format(
                        selection_rule["min_data_samples"], client.get("data_samples", 0)
                    )
                ) 