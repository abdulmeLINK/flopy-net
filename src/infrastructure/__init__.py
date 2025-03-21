"""
Infrastructure Layer

This layer contains implementations of interfaces defined in the domain layer,
adapters for external libraries, and other infrastructure concerns.

Components:
- repositories: Data storage implementations
- clients: External client/server adapters
- config: Configuration management
"""

from src.infrastructure.repositories import *
from src.infrastructure.clients import *
from src.infrastructure.config import *

__all__ = [
    # Include all exported symbols here
] 