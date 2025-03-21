"""
Register FL Strategies

This module registers all available federated learning strategies
with the strategy registry.
"""
import logging

from src.application.fl_strategies.registry import register_strategy
from src.application.fl_strategies.fed_avg_strategy import FedAvgStrategy
from src.application.fl_strategies.fed_prox_strategy import FedProxStrategy

logger = logging.getLogger(__name__)

def register_all_strategies():
    """
    Register all available FL strategies with the strategy registry.
    
    Call this function during application startup to ensure all strategies
    are available.
    """
    logger.info("Registering FL strategies...")
    
    # FedAvg strategy
    register_strategy("fedavg", FedAvgStrategy)
    logger.debug("Registered fedavg strategy")
    
    # FedProx strategy
    register_strategy("fedprox", FedProxStrategy)
    logger.debug("Registered fedprox strategy")
    
    # Add more strategy registrations here as they are implemented
    
    logger.info("FL strategy registration complete") 