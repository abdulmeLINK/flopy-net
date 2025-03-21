"""
SDN Infrastructure Module

This module contains implementations for SDN controllers and network simulators.
"""

from typing import Dict, Type, Any

# Import SDN controller implementations
from .onos_controller import ONOSController
from .ryu_controller import RyuController

# Import network simulator implementations
from .mininet_simulator import MininetSimulator
from .mock_simulator import MockNetworkSimulator

# Available SDN controller implementations
SDN_CONTROLLERS: Dict[str, Type] = {
    "onos": ONOSController,
    "ryu": RyuController,
}

# Available network simulator implementations
NETWORK_SIMULATORS: Dict[str, Type] = {
    "mininet": MininetSimulator,
    "mock": MockNetworkSimulator,
}

__all__ = [
    "ONOSController",
    "RyuController",
    "MininetSimulator",
    "MockNetworkSimulator",
    "SDN_CONTROLLERS",
    "NETWORK_SIMULATORS",
] 