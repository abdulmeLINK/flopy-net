#!/usr/bin/env python
"""
Test Mininet Topology Integration

This script tests loading and using topologies from the simulation/topologies directory
with Mininet for network emulation in the federated learning system.
"""

import sys
import os
import time
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src directory to path
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
scripts_dir = project_root / "scripts"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

def list_available_topologies():
    """List all available topology files."""
    topologies_dir = src_dir / "simulation" / "topologies"
    if not topologies_dir.exists():
        logger.error(f"Topologies directory not found: {topologies_dir}")
        return []
    
    topology_files = [f for f in os.listdir(topologies_dir) if f.endswith('.json')]
    logger.info(f"Found {len(topology_files)} topology files:")
    for topo in topology_files:
        logger.info(f"  - {topo}")
    
    return topology_files

def test_load_topology(topology_name="standard_topology.json"):
    """Test loading a specific topology file into a NetworkTopology object."""
    try:
        from simulation.utils import load_topology_from_json
        
        topology_path = src_dir / "simulation" / "topologies" / topology_name
        if not topology_path.exists():
            logger.error(f"Topology file not found: {topology_path}")
            return False
        
        logger.info(f"Loading topology from {topology_path}")
        topology = load_topology_from_json(str(topology_path))
        
        logger.info(f"Successfully loaded topology: {topology.name}")
        logger.info(f"  - Nodes: {len(topology.nodes)}")
        logger.info(f"  - Links: {len(topology.links)}")
        
        # Print node details
        logger.info("Node details:")
        for node in topology.nodes:
            logger.info(f"  - {node.id} (type: {node.type})")
        
        # Print link details
        logger.info("Link details:")
        for link in topology.links:
            props = []
            if hasattr(link, "bandwidth") and link.bandwidth:
                props.append(f"bw={link.bandwidth}")
            if hasattr(link, "delay") and link.delay:
                props.append(f"delay={link.delay}")
            if hasattr(link, "loss") and link.loss:
                props.append(f"loss={link.loss}")
            
            logger.info(f"  - {link.nodes[0]}-{link.nodes[1]} ({', '.join(props)})")
        
        return True
    
    except ImportError as e:
        logger.error(f"Error importing required modules: {e}")
        return False
    except Exception as e:
        logger.error(f"Error loading topology: {e}")
        return False

def test_mininet_integration(topology_name="standard_topology.json"):
    """Test loading a topology into Mininet."""
    try:
        # Import Mininet integration
        from mininet_integration import MininetIntegration
        
        # Create a Mininet integration instance
        logger.info("Creating MininetIntegration instance")
        mn_integration = MininetIntegration()
        
        # Check if Mininet is properly installed
        try:
            import mininet
            logger.info("Mininet is properly installed")
        except ImportError:
            logger.error("Mininet is not installed, skipping test")
            return False
        
        # Extract topology name without extension if needed
        if topology_name.endswith('.json'):
            topology_name = topology_name[:-5]
        
        # Enable Mininet with the specified topology
        logger.info(f"Enabling Mininet with topology: {topology_name}")
        result = mn_integration.enable(topology_name)
        
        if not result:
            logger.error("Failed to enable Mininet with the specified topology")
            return False
        
        logger.info("Successfully enabled Mininet with the topology")
        
        # Check hosts and links
        logger.info(f"Number of hosts: {len(mn_integration.hosts)}")
        logger.info(f"Hosts: {', '.join(mn_integration.hosts.keys())}")
        
        # Apply some network conditions
        test_conditions = {
            "server-s1": {"delay": "50ms", "loss": 2},
            "client1-s1": {"delay": "100ms", "loss": 5}
        }
        
        logger.info("Applying test network conditions")
        mn_integration.apply_network_conditions(test_conditions)
        
        # Let it run for a moment
        logger.info("Running Mininet for 5 seconds")
        time.sleep(5)
        
        # Disable Mininet
        logger.info("Disabling Mininet")
        mn_integration.disable()
        
        return True
    
    except ImportError as e:
        logger.error(f"Error importing Mininet integration: {e}")
        return False
    except Exception as e:
        logger.error(f"Error testing Mininet integration: {e}")
        return False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test Mininet topology integration")
    parser.add_argument("--topology", default="standard_topology.json",
                      help="Name of the topology file to test")
    parser.add_argument("--list-only", action="store_true",
                      help="Only list available topologies without testing")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # List available topologies
    topology_files = list_available_topologies()
    if not topology_files:
        logger.error("No topology files found")
        return 1
    
    # Exit if only listing topologies
    if args.list_only:
        return 0
    
    # Check if specified topology exists
    if args.topology not in topology_files and args.topology + ".json" not in topology_files:
        logger.error(f"Specified topology '{args.topology}' not found")
        logger.info("Available topologies: " + ", ".join(topology_files))
        return 1
    
    # Test loading the topology
    logger.info(f"Testing topology: {args.topology}")
    if not test_load_topology(args.topology):
        logger.error("Failed to load topology")
        return 1
    
    # Test Mininet integration
    logger.info("Testing Mininet integration")
    if not test_mininet_integration(args.topology):
        logger.error("Failed to test Mininet integration")
        return 1
    
    logger.info("All tests completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 