"""
Policy implementation for financial services scenarios.

This module provides policy definitions specific to financial services,
focusing on secure aggregation, PCI DSS compliance, and fraud detection.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional

from src.core.policies.policy import Policy

logger = logging.getLogger(__name__)


class FinancialPolicy(Policy):
    """
    Financial services policy for federated learning.
    
    This policy enforces requirements for financial services scenarios such as:
    - PCI DSS compliance
    - Secure aggregation
    - Multi-party computation
    - Fraud detection security
    """
    
    def __init__(self, policy_id: str = None, name: str = None, rules: Optional[Dict[str, Any]] = None):
        """
        Initialize a financial services policy.
        
        Args:
            policy_id: Unique identifier for the policy
            name: Human-readable name for the policy
            rules: Dictionary of policy rules
        """
        policy_id = policy_id or f"financial-policy-{uuid.uuid4()}"
        name = name or "Financial Services Policy"
        
        # Default rules for financial services
        default_rules = {
            "pci_dss": {
                "secure_aggregation_required": True,
                "min_parties_for_aggregation": 3,
                "differential_privacy_required": True,
                "epsilon_max": 1.0,
                "delta_max": 1e-5
            },
            "secure_aggregation": {
                "enabled": True,
                "threshold": 0.8,
                "timeout_seconds": 300
            },
            "client_selection": {
                "min_data_samples": 1000,
                "certified_only": True,
                "geographical_distribution": {
                    "enabled": True,
                    "max_same_region": 0.6  # At most 60% from the same region
                }
            },
            "fraud_detection": {
                "min_auc_required": 0.85,
                "max_false_negative_rate": 0.15,
                "model_update_frequency_hours": 24
            },
            "data_protection": {
                "pii_removal_required": True,
                "data_retention_days": 90,
                "encryption_required": True
            }
        }
        
        # Merge provided rules with defaults
        merged_rules = default_rules.copy()
        if rules:
            for category, category_rules in rules.items():
                if category in merged_rules:
                    merged_rules[category].update(category_rules)
                else:
                    merged_rules[category] = category_rules
        
        super().__init__(
            policy_id=policy_id,
            name=name,
            policy_type="financial_services",
            rules=merged_rules
        )
        
        logger.info(f"Initialized financial policy with ID: {policy_id}")
    
    def verify_pci_compliance(self, model_metadata: Dict[str, Any]) -> bool:
        """
        Verify PCI DSS compliance for the given model.
        
        Args:
            model_metadata: Metadata of the model to check
            
        Returns:
            True if compliant, False otherwise
        """
        # Check if secure aggregation is enabled
        security = model_metadata.get('security', {})
        secure_agg_enabled = security.get('secure_aggregation_enabled', False)
        
        if not secure_agg_enabled and self.rules['pci_dss']['secure_aggregation_required']:
            logger.warning("PCI compliance verification failed: secure aggregation not enabled")
            return False
        
        # Check if min_parties is sufficient
        min_parties = security.get('min_parties', 0)
        if min_parties < self.rules['pci_dss']['min_parties_for_aggregation']:
            logger.warning(f"PCI compliance verification failed: min_parties={min_parties} < required={self.rules['pci_dss']['min_parties_for_aggregation']}")
            return False
        
        # Check if differential privacy is applied when required
        if self.rules['pci_dss']['differential_privacy_required']:
            privacy = model_metadata.get('privacy', {})
            dp_applied = privacy.get('differential_privacy_applied', False)
            
            if not dp_applied:
                logger.warning("PCI compliance verification failed: differential privacy not applied")
                return False
            
            # Check epsilon and delta are within limits
            epsilon = privacy.get('epsilon', float('inf'))
            delta = privacy.get('delta', 1.0)
            
            if epsilon > self.rules['pci_dss']['epsilon_max']:
                logger.warning(f"PCI compliance verification failed: epsilon={epsilon} > max={self.rules['pci_dss']['epsilon_max']}")
                return False
                
            if delta > self.rules['pci_dss']['delta_max']:
                logger.warning(f"PCI compliance verification failed: delta={delta} > max={self.rules['pci_dss']['delta_max']}")
                return False
        
        logger.info("PCI DSS compliance verification passed")
        return True
    
    def verify_client_eligibility(self, client_metadata: Dict[str, Any]) -> bool:
        """
        Verify if a client is eligible to participate in financial federated learning.
        
        Args:
            client_metadata: Metadata of the client to check
            
        Returns:
            True if eligible, False otherwise
        """
        # Check if client has sufficient data
        data_samples = client_metadata.get('data_samples', 0)
        if data_samples < self.rules['client_selection']['min_data_samples']:
            logger.warning(f"Client eligibility verification failed: data_samples={data_samples} < required={self.rules['client_selection']['min_data_samples']}")
            return False
        
        # Check if client is certified when required
        if self.rules['client_selection']['certified_only']:
            certified = client_metadata.get('certified', False)
            if not certified:
                logger.warning("Client eligibility verification failed: client not certified")
                return False
        
        # Check for PCI compliance
        pci_compliant = client_metadata.get('pci_compliant', False)
        if not pci_compliant:
            logger.warning("Client eligibility verification failed: client not PCI compliant")
            return False
        
        logger.info("Client eligibility verification passed")
        return True
    
    def calculate_client_weight(self, client_metadata: Dict[str, Any]) -> float:
        """
        Calculate the weight of a client for aggregation.
        
        Args:
            client_metadata: Metadata of the client
            
        Returns:
            Weight of the client (0.0-1.0)
        """
        # Base weight based on data samples
        data_samples = client_metadata.get('data_samples', 0)
        min_samples = self.rules['client_selection']['min_data_samples']
        
        # Normalize based on minimum requirement (with a cap)
        base_weight = min(1.0, data_samples / (min_samples * 5))
        
        # Adjust for certification
        if client_metadata.get('certified', False):
            base_weight *= 1.2  # Bonus for certified clients
        
        # Adjust for performance metrics if available
        if 'performance' in client_metadata:
            performance = client_metadata['performance']
            
            # Fraud detection quality boosts weight
            if 'auc' in performance:
                auc = performance['auc']
                min_auc = self.rules['fraud_detection']['min_auc_required']
                if auc >= min_auc:
                    auc_factor = 1.0 + 0.5 * ((auc - min_auc) / (1.0 - min_auc))
                    base_weight *= auc_factor
            
            # Penalize high false negative rates
            if 'false_negative_rate' in performance:
                fnr = performance['false_negative_rate']
                max_fnr = self.rules['fraud_detection']['max_false_negative_rate']
                if fnr > max_fnr:
                    base_weight *= (1.0 - (fnr - max_fnr))
        
        # Ensure weight is between 0 and 1
        return max(0.0, min(1.0, base_weight))
    
    def get_policy_requirements(self) -> Dict[str, Any]:
        """
        Get the policy requirements for financial services.
        
        Returns:
            Dictionary of policy requirements
        """
        return {
            "pci_dss_compliance": {
                "required": True,
                "secure_aggregation": self.rules['pci_dss']['secure_aggregation_required'],
                "min_parties": self.rules['pci_dss']['min_parties_for_aggregation'],
                "differential_privacy": self.rules['pci_dss']['differential_privacy_required'],
                "epsilon_max": self.rules['pci_dss']['epsilon_max'],
                "delta_max": self.rules['pci_dss']['delta_max']
            },
            "client_requirements": {
                "min_data_samples": self.rules['client_selection']['min_data_samples'],
                "certified_only": self.rules['client_selection']['certified_only']
            },
            "fraud_detection_requirements": {
                "min_auc": self.rules['fraud_detection']['min_auc_required'],
                "max_false_negative_rate": self.rules['fraud_detection']['max_false_negative_rate'],
                "model_update_frequency_hours": self.rules['fraud_detection']['model_update_frequency_hours']
            },
            "data_protection": {
                "pii_removal_required": self.rules['data_protection']['pii_removal_required'],
                "data_retention_days": self.rules['data_protection']['data_retention_days'],
                "encryption_required": self.rules['data_protection']['encryption_required']
            }
        } 