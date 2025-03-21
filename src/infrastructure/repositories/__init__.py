"""
Repositories

This package provides repository implementations for the federated learning system.
"""

from src.infrastructure.repositories.client_repository import InMemoryClientRepository
from src.infrastructure.repositories.fl_model_repository import FileModelRepository

__all__ = [
    'InMemoryClientRepository',
    'FileModelRepository'
] 