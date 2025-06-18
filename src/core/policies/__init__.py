"""
Policies for federated learning.

This package contains policy implementations for federated learning,
including domain-specific policies, privacy policies, and aggregation policies.
"""

from src.core.policies.policy import Policy, IPolicy
from src.core.policies.privacy_policy import PrivacyPolicy
from src.core.policies.basic_policy import BasicPolicy
from src.core.policies.policy_registry import PolicyRegistry, get_policy_registry

__all__ = [
    'Policy',
    'IPolicy',
    'PrivacyPolicy',
    'BasicPolicy',
    'PolicyRegistry',
    'get_policy_registry'
]
