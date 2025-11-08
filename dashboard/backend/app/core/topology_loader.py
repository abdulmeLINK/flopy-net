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

import os
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Global variable to hold the TopologyManager class
TopologyManager = None

def _import_topology_manager():
    """Dynamically import the TopologyManager from src directory."""
    global TopologyManager
    
    if TopologyManager is not None:
        return TopologyManager
    
    # Try multiple import strategies
    import_attempts = [
        # Direct import (works when src is in PYTHONPATH)
        lambda: __import__('src.utils.topology_manager', fromlist=['TopologyManager']).TopologyManager,
        
        # Try adding src to path and importing
        lambda: _import_with_path_adjustment(),
        
        # Fallback to a mock class
        lambda: _create_mock_topology_manager()
    ]
    
    for attempt in import_attempts:
        try:
            TopologyManager = attempt()
            if TopologyManager:
                logger.info("Successfully imported TopologyManager")
                return TopologyManager
        except Exception as e:
            logger.debug(f"TopologyManager import attempt failed: {e}")
            continue
    
    # If all attempts fail, use the mock class
    logger.warning("Using mock TopologyManager - src directory not available")
    TopologyManager = _create_mock_topology_manager()
    return TopologyManager

def _import_with_path_adjustment():
    """Try to import by adjusting the Python path."""
    # Try different possible locations for the src directory
    possible_src_paths = [
        Path(__file__).resolve().parents[3] / 'src',  # ../../../src from this file
        Path('/app/src'),  # Docker container path
        Path.cwd() / 'src',  # Current working directory
        Path.cwd().parent / 'src',  # Parent of current working directory
    ]
    
    for src_path in possible_src_paths:
        if src_path.exists():
            parent_path = str(src_path.parent)
            if parent_path not in sys.path:
                sys.path.insert(0, parent_path)
            
            try:
                from src.utils.topology_manager import TopologyManager
                logger.info(f"Successfully imported TopologyManager from {src_path}")
                return TopologyManager
            except ImportError as e:
                logger.debug(f"Failed to import TopologyManager from {src_path}: {e}")
                continue
    
    return None

def _create_mock_topology_manager():
    """Create a mock TopologyManager for when the real one is not available."""
    class MockTopologyManager:
        def __init__(self, topology_file=None):
            self.topology_file = topology_file
            self.topology_config = self._load_mock_config()
            logger.warning("Using mock TopologyManager - real TopologyManager not available")
        
        def _load_mock_config(self):
            """Return a mock topology configuration."""
            return {
                "nodes": [
                    {
                        "id": "fl-server",
                        "name": "FL Server",
                        "type": "fl-server",
                        "ip": "192.168.100.100"
                    },
                    {
                        "id": "fl-client-1",
                        "name": "FL Client 1",
                        "type": "fl-client",
                        "ip": "192.168.100.101"
                    },
                    {
                        "id": "fl-client-2",
                        "name": "FL Client 2",
                        "type": "fl-client",
                        "ip": "192.168.100.102"
                    }
                ],
                "links": [
                    {
                        "source": "fl-server",
                        "target": "fl-client-1",
                        "bandwidth": "100Mbps"
                    },
                    {
                        "source": "fl-server",
                        "target": "fl-client-2",
                        "bandwidth": "100Mbps"
                    }
                ]
            }
    
    return MockTopologyManager

class TopologyLoader:
    @staticmethod
    def load_from_file(topology_file: str) -> Dict[str, Any]:
        if not os.path.exists(topology_file):
            raise FileNotFoundError(f"Topology file not found: {topology_file}")
        
        TopologyManagerClass = _import_topology_manager()
        tm = TopologyManagerClass(topology_file=topology_file)
        if not tm.topology_config:
            raise ValueError("Failed to load topology config")
        return {
            "nodes": tm.topology_config.get("nodes", []),
            "links": tm.topology_config.get("links", [])
        }

    @staticmethod
    async def aload_from_file(topology_file: str) -> Dict[str, Any]:
        # For compatibility, just call sync version
        return TopologyLoader.load_from_file(topology_file) 