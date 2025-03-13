"""
Dashboard Package

This package provides a dashboard for federated learning.
"""

__version__ = "1.0.0"

# Handle imports that might fail if modules don't exist yet
try:
    from dashboard.api import app as api_app
    
    # Optional modules
    try:
        from dashboard.utils import DashboardConnector, MockDataGenerator
        __all__ = ["DashboardConnector", "MockDataGenerator", "api_app"]
    except ImportError:
        __all__ = ["api_app"]
except ImportError:
    # Define an empty __all__ if nothing can be imported
    __all__ = [] 