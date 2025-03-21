"""
Client implementations

This package contains external client implementations like Flower clients.
"""

from src.infrastructure.clients.flower_client import FlowerClient
from src.infrastructure.clients.flower_server import FlowerServer

__all__ = [
    'FlowerClient',
    'FlowerServer'
] 