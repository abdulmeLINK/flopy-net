"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
Collector API Routes Package.

This package contains modular Flask Blueprint routes for the collector API.
Each module handles a specific domain of routes.

Modules:
- fl_routes: Federated learning metrics endpoints (/metrics/fl/*)
- network_routes: Network topology and metrics endpoints (/network/*)
"""

from .fl_routes import fl_bp, init_fl_routes
from .network_routes import network_bp, init_network_routes

__all__ = [
    'fl_bp',
    'init_fl_routes',
    'network_bp',
    'init_network_routes',
]
