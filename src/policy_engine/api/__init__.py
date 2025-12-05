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
Policy Engine API Routes Package

This package contains Flask Blueprint routes for the Policy Engine API.
"""

from src.policy_engine.api.policy_routes import (
    policy_bp,
    init_policy_routes,
)
from src.policy_engine.api.function_routes import (
    function_bp,
    init_function_routes,
)
from src.policy_engine.api.metrics_routes import (
    metrics_bp,
    init_metrics_routes,
)

__all__ = [
    'policy_bp',
    'init_policy_routes',
    'function_bp', 
    'init_function_routes',
    'metrics_bp',
    'init_metrics_routes',
]
