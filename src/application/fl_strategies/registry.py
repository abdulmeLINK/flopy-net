"""
Federated Learning Strategy Registry

This module provides a registry for FL strategy classes, allowing strategies
to be registered, retrieved, and instantiated by name.
"""
from typing import Dict, Type, Any

from src.domain.interfaces.fl_strategy import IFLStrategy

# Dictionary mapping strategy names to strategy classes
strategy_registry: Dict[str, Type[IFLStrategy]] = {}

def register_strategy(strategy_name: str, strategy_class: Type[IFLStrategy]) -> None:
    """
    Register a strategy class by name.
    
    Args:
        strategy_name: Name to register the strategy as
        strategy_class: Strategy class to register
    """
    if strategy_name in strategy_registry:
        raise ValueError(f"Strategy {strategy_name} is already registered")
    
    strategy_registry[strategy_name] = strategy_class

def get_strategy_class(strategy_name: str) -> Type[IFLStrategy]:
    """
    Get a strategy class by name.
    
    Args:
        strategy_name: Name of the strategy to get
        
    Returns:
        Strategy class
        
    Raises:
        KeyError: If the strategy is not registered
    """
    if strategy_name not in strategy_registry:
        raise KeyError(f"Strategy {strategy_name} is not registered")
    
    return strategy_registry[strategy_name]

def create_strategy(strategy_name: str, config: Dict[str, Any] = None) -> IFLStrategy:
    """
    Create a strategy instance by name.
    
    Args:
        strategy_name: Name of the strategy to create
        config: Configuration for the strategy
        
    Returns:
        Strategy instance
        
    Raises:
        KeyError: If the strategy is not registered
    """
    strategy_class = get_strategy_class(strategy_name)
    return strategy_class(config=config or {})

def list_strategies() -> Dict[str, str]:
    """
    Get a list of all registered strategies.
    
    Returns:
        Dictionary mapping strategy names to descriptions
    """
    return {
        name: cls(config={}).get_description()
        for name, cls in strategy_registry.items()
    } 