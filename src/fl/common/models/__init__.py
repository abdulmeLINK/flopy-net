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

# FL Common Models Package
__version__ = "1.0.0"

# Import common model classes for easier access
try:
    from .simple_models import SimpleCNN, SimpleMLP
    __all__ = ['SimpleCNN', 'SimpleMLP']
except ImportError:
    # If simple_models doesn't exist yet, just define the package
    __all__ = [] 