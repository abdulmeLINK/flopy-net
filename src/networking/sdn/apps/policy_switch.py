"""
Policy-Aware Ryu OpenFlow Controller Application for Federated Learning Network.

This Ryu application provides comprehensive SDN functionality including:
- Policy enforcement from Policy Engine
- Network topology discovery and management  
- REST API endpoints for network monitoring
- Learning switch functionality with policy integration

Refactored version with modular architecture for better maintainability.
"""

import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Try relative imports first (when run as part of package)
    from .policy_switch_core import PolicySwitchCore
    from .policy_engine_mixin import PolicyEngineMixin
    from .policy_switch_api import PolicySwitchRESTController
except ImportError:
    # Fall back to direct imports (when run standalone)
    try:
        from policy_switch_core import PolicySwitchCore
        from policy_engine_mixin import PolicyEngineMixin
        from policy_switch_api import PolicySwitchRESTController
    except ImportError as e:
        print(f"Import error: {e}")
        print(f"Current directory: {current_dir}")
        print(f"Python path: {sys.path}")
        raise


class PolicySwitch(PolicySwitchCore, PolicyEngineMixin):
    """
    Policy-aware switch controller that enforces network security policies.
    
    This is the main PolicySwitch class that combines core functionality
    with policy engine integration.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the Policy Switch Controller."""
        super(PolicySwitch, self).__init__(*args, **kwargs)
        
        # Start policy polling (now that we have access to PolicyEngineMixin methods)
        from ryu.lib import hub
        hub.spawn(self._policy_poll_loop)
        
        # Set up REST API
        wsgi = kwargs['wsgi']
        wsgi.register(PolicySwitchRESTController, {'policy_switch_app': self})
