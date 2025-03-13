"""
Policy Engine Package

This package provides a policy engine for federated learning.
"""

__version__ = "1.0.0"

# Imports that depend on modules that might not exist yet are placed in a try-except block
# This allows the package to be imported even if some modules are missing
try:
    from .app import app
    
    # Import these modules only if they exist
    try:
        from .models import (
            Policy, PolicyCreate, PolicyUpdate, PolicyResponse, PoliciesResponse,
            Condition, Action
        )
        from .storage import get_policy_storage, PolicyStorage
        from .interpreter import interpreter, PolicyInterpreter
    except ImportError:
        # These modules are optional and may not exist in minimal implementations
        pass
except ImportError:
    # The app module is required, but we'll handle its absence gracefully
    pass 