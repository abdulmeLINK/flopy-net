"""
Federated Learning Strategies

This module provides various federated learning strategies for the system,
including aggregation methods and communication protocols.
"""

from src.application.fl_strategies.registry import register_strategy, create_strategy, list_strategies
from src.application.fl_strategies.register_strategies import register_all_strategies

__all__ = [
    'register_strategy',
    'create_strategy',
    'list_strategies',
    'register_all_strategies'
] 