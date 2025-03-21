"""
Test Metrics Generator

This script generates sample metrics and sends them to the metrics API,
helpful for testing the API when the full simulation isn't running.
"""

import time
import random
import json
import requests
import logging
import argparse
import threading
import math
import platform
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample metrics data
SAMPLE_DATA = {
    "accuracy": 0.0,
    "loss": 1.0,
    "latency": 100,
    "bandwidth": 10,
    "client_participation": 3
}

# System status
SYSTEM_STATUS = {
    "status": "running",
    "current_round": 0,
    "total_rounds": 10,
    "start_time": time.time()
}

# Active challenges
ACTIVE_CHALLENGES = [
    {
        "name": "high_latency",
        "type": "HighLatency",
        "intensity": 0.5,
        "active": True
    },
    {
        "name": "packet_loss",
        "type": "PacketLoss",
        "intensity": 0.2,
        "active": True
    }
]

# Client information
CLIENTS = {
    "client_0": {
        "id": "client_0",
        "status": "active",
        "data_size": 1000,
        "compute_power": 1.0,
        "last_active": time.time()
    },
    "client_1": {
        "id": "client_1",
        "status": "active",
        "data_size": 1500,
        "compute_power": 0.8,
        "last_active": time.time()
    },
    "client_2": {
        "id": "client_2",
        "status": "active",
        "data_size": 800,
        "compute_power": 1.2,
        "last_active": time.time()
    }
}

# Network topology
NETWORK = {
    "topology": {
        "nodes": [
            {
                "id": "server",
                "type": "host",
                "ip": "10.0.0.1",
                "mac": "00:00:00:00:00:01",
                "interfaces": ["server-eth0"]
            },
            {
                "id": "client_0",
                "type": "host",
                "ip": "10.0.0.2",
                "mac": "00:00:00:00:00:02",
                "interfaces": ["client_0-eth0"]
            },
            {
                "id": "client_1",
                "type": "host",
                "ip": "10.0.0.3",
                "mac": "00:00:00:00:00:03",
                "interfaces": ["client_1-eth0"]
            },
            {
                "id": "client_2",
                "type": "host",
                "ip": "10.0.0.4",
                "mac": "00:00:00:00:00:04",
                "interfaces": ["client_2-eth0"]
            },
            {
                "id": "s1",
                "type": "switch",
                "dpid": "1",
                "interfaces": ["s1-eth0", "s1-eth1", "s1-eth2", "s1-eth3"]
            }
        ],
        "links": [
            {
                "id": "server-s1",
                "nodes": ["server", "s1"],
                "bandwidth": 100,
                "delay": "1ms",
                "loss": 0
            },
            {
                "id": "client_0-s1",
                "nodes": ["client_0", "s1"],
                "bandwidth": 20,
                "delay": "5ms",
                "loss": 0
            },
            {
                "id": "client_1-s1",
                "nodes": ["client_1", "s1"],
                "bandwidth": 10,
                "delay": "10ms",
                "loss": 0
            },
            {
                "id": "client_2-s1",
                "nodes": ["client_2", "s1"],
                "bandwidth": 5,
                "delay": "20ms",
                "loss": 0
            }
        ],
        "congestion_points": []  # Will be calculated dynamically
    },
    "client_connections": {},  # Will be populated below
    "link_utilization": {},    # Will be populated below
    "packet_drops": {},        # Will be populated below
    "latency_map": {},         # Will be populated below
    "bandwidth_map": {}        # Will be populated below
}

# Populate client connections
for client_id in CLIENTS.keys():
    client_links = [link for link in NETWORK["topology"]["links"] if client_id in link["nodes"]]
    NETWORK["client_connections"][client_id] = {
        "links": [link["id"] for link in client_links],
        "bandwidth": client_links[0]["bandwidth"] if client_links else 0,
        "delay": client_links[0]["delay"] if client_links else "0ms",
        "loss": client_links[0]["loss"] if client_links else 0
    }

# Populate link utilization
for link in NETWORK["topology"]["links"]:
    NETWORK["link_utilization"][link["id"]] = 0.1  # Initial utilization 10%

# Populate packet drops
for link in NETWORK["topology"]["links"]:
    NETWORK["packet_drops"][link["id"]] = 0  # Initial packet drops

# Populate latency map (node-to-node latency)
NETWORK["latency_map"] = {
    "server-client_0": "5ms",
    "server-client_1": "10ms",
    "server-client_2": "20ms",
    "client_0-client_1": "15ms",
    "client_0-client_2": "25ms",
    "client_1-client_2": "30ms"
}

# Populate bandwidth map (node-to-node bandwidth)
NETWORK["bandwidth_map"] = {
    "server-client_0": 20,
    "server-client_1": 10,
    "server-client_2": 5,
    "client_0-client_1": 10,
    "client_0-client_2": 5,
    "client_1-client_2": 5
}

# Policy information
POLICY = {
    "active_policies": [
        {
            "id": "policy_1",
            "name": "BandwidthAllocationPolicy",
            "type": "ResourceAllocationPolicy",
            "priority": 10,
            "enabled": True
        },
        {
            "id": "policy_2",
            "name": "ClientSelectionPolicy",
            "type": "ClientManagementPolicy",
            "priority": 5,
            "enabled": True
        },
        {
            "id": "policy_3",
            "name": "CongestionAvoidancePolicy",
            "type": "NetworkOptimizationPolicy",
            "priority": 8,
            "enabled": True
        }
    ],
    "policy_decisions": [
        {
            "policy_id": "policy_1",
            "timestamp": time.time() - 60,
            "decision": "Allocated 5Mbps extra bandwidth to client_0",
            "reason": "High training performance"
        },
        {
            "policy_id": "policy_3",
            "timestamp": time.time() - 30,
            "decision": "Rerouted traffic around congested link client_1-s1",
            "reason": "High packet loss detected"
        }
    ],
    "optimization_metrics": {
        "bandwidth_saved": 15.5,  # MB
        "latency_reduced": 12.3,  # ms
        "throughput_increased": 8.7  # Mbps
    },
    "resource_allocation": {
        "client_0": {
            "bandwidth": 25,  # Mbps
            "priority": "high"
        },
        "client_1": {
            "bandwidth": 10,  # Mbps
            "priority": "medium"
        },
        "client_2": {
            "bandwidth": 5,  # Mbps
            "priority": "low"
        }
    }
}


def generate_metrics(round_num, total_rounds):
    """Generate sample metrics for a specific round."""
    progress = round_num / total_rounds
    
    # Accuracy increases over time with some randomness
    accuracy = 0.5 + 0.4 * progress + random.uniform(-0.05, 0.05)
    accuracy = min(max(accuracy, 0.0), 1.0)  # Clamp between 0 and 1
    
    # Loss decreases over time with some randomness
    loss = 1.0 - 0.8 * progress + random.uniform(-0.1, 0.1)
    loss = max(loss, 0.05)  # Ensure loss is always positive
    
    # Latency varies with some spikes
    latency = 50 + 30 * math.sin(round_num) + random.uniform(-10, 30)
    
    # Bandwidth varies
    bandwidth = 10 + 5 * math.cos(round_num) + random.uniform(-2, 5)
    
    # Client participation varies
    client_participation = random.randint(2, 3)
    
    return {
        "accuracy": round(accuracy, 4),
        "loss": round(loss, 4),
        "latency": round(latency, 2),
        "bandwidth": round(bandwidth, 2),
        "client_participation": client_participation,
        "round": round_num,
        "timestamp": time.time()
    }


def update_network_metrics(round_num):
    """Update network metrics to simulate changing conditions."""
    # Update link utilization based on round number
    for link_id in NETWORK["link_utilization"]:
        # Create a pattern of utilization that varies over rounds
        base_utilization = 0.2 + 0.1 * math.sin(round_num * 0.5)
        
        # Add specific congestion to client_1's link sometimes
        if link_id == "client_1-s1" and round_num % 3 == 0:
            base_utilization += 0.6  # Congestion spike
        
        # Add randomness
        utilization = base_utilization + random.uniform(-0.05, 0.15)
        NETWORK["link_utilization"][link_id] = max(min(utilization, 0.95), 0.05)  # Clamp between 5% and 95%
    
    # Update packet drops based on utilization
    for link_id in NETWORK["packet_drops"]:
        utilization = NETWORK["link_utilization"][link_id]
        
        # Higher utilization leads to more packet drops
        if utilization > 0.8:
            NETWORK["packet_drops"][link_id] = random.randint(8, 15)  # High packet loss
        elif utilization > 0.6:
            NETWORK["packet_drops"][link_id] = random.randint(2, 7)   # Medium packet loss
        else:
            NETWORK["packet_drops"][link_id] = random.randint(0, 1)   # Low/no packet loss
    
    # Update congestion points based on utilization and packet drops
    congestion_points = []
    for link_id, utilization in NETWORK["link_utilization"].items():
        drops = NETWORK["packet_drops"][link_id]
        
        if utilization > 0.8 or drops > 10:
            congestion_points.append({
                "link_id": link_id,
                "reason": "high_utilization" if utilization > 0.8 else "high_packet_loss",
                "severity": "high",
                "utilization": round(utilization * 100, 1),
                "packet_loss": drops
            })
        elif utilization > 0.6 or drops > 5:
            congestion_points.append({
                "link_id": link_id,
                "reason": "medium_utilization" if utilization > 0.6 else "medium_packet_loss",
                "severity": "medium",
                "utilization": round(utilization * 100, 1),
                "packet_loss": drops
            })
    
    NETWORK["topology"]["congestion_points"] = congestion_points
    
    # Update client connections based on current network state
    for client_id in CLIENTS.keys():
        client_links = [link for link in NETWORK["topology"]["links"] if client_id in link["nodes"]]
        if client_links:
            link = client_links[0]
            link_id = link["id"]
            NETWORK["client_connections"][client_id] = {
                "links": [link_id],
                "bandwidth": link["bandwidth"],
                "delay": link["delay"],
                "loss": NETWORK["packet_drops"][link_id],
                "utilization": round(NETWORK["link_utilization"][link_id] * 100, 1)
            }


def update_policy_metrics(round_num):
    """Update policy metrics to simulate policy engine activity."""
    # Add a new policy decision periodically
    if round_num % 2 == 0:
        # Choose a random policy
        policy = random.choice(POLICY["active_policies"])
        
        # Generate a random decision based on policy type
        if policy["type"] == "ResourceAllocationPolicy":
            client = f"client_{random.randint(0, 2)}"
            bandwidth = random.randint(5, 25)
            decision = f"Allocated {bandwidth}Mbps bandwidth to {client}"
            reason = "Optimizing resource distribution"
        elif policy["type"] == "ClientManagementPolicy":
            client = f"client_{random.randint(0, 2)}"
            decision = f"Prioritized {client} for next round"
            reason = "Based on data quality assessment"
        else:  # NetworkOptimizationPolicy
            link_id = random.choice([l["id"] for l in NETWORK["topology"]["links"]])
            decision = f"Optimized routing around {link_id}"
            reason = "Detected network congestion"
        
        # Add the decision to the list (keep only the most recent 5)
        POLICY["policy_decisions"].insert(0, {
            "policy_id": policy["id"],
            "timestamp": time.time(),
            "decision": decision,
            "reason": reason
        })
        
        # Keep only the 5 most recent decisions
        POLICY["policy_decisions"] = POLICY["policy_decisions"][:5]
    
    # Update optimization metrics
    POLICY["optimization_metrics"]["bandwidth_saved"] += random.uniform(0.1, 0.5)
    POLICY["optimization_metrics"]["latency_reduced"] += random.uniform(0.05, 0.2)
    POLICY["optimization_metrics"]["throughput_increased"] += random.uniform(0.1, 0.3)
    
    # Round the values for readability
    for key in POLICY["optimization_metrics"]:
        POLICY["optimization_metrics"][key] = round(POLICY["optimization_metrics"][key], 2)
    
    # Update resource allocation based on network conditions
    for client_id, connection in NETWORK["client_connections"].items():
        POLICY["resource_allocation"][client_id]["bandwidth"] = connection["bandwidth"]
        
        # Adjust priority based on connection quality
        if connection.get("utilization", 0) > 80 or connection.get("loss", 0) > 10:
            POLICY["resource_allocation"][client_id]["priority"] = "low"  # Bad connection
        elif connection.get("utilization", 0) < 30 and connection.get("loss", 0) < 2:
            POLICY["resource_allocation"][client_id]["priority"] = "high"  # Good connection
        else:
            POLICY["resource_allocation"][client_id]["priority"] = "medium"  # Average connection


def update_client_status(round_num):
    """Update client status to simulate client behavior."""
    # Update client status periodically
    for client_id in CLIENTS:
        # Determine if client should be active based on round and random chance
        if round_num % 4 == 0 and client_id == "client_2" and random.random() < 0.5:
            CLIENTS[client_id]["status"] = "inactive"  # client_2 sometimes goes offline
        else:
            CLIENTS[client_id]["status"] = "active"
        
        # Update last active timestamp for active clients
        if CLIENTS[client_id]["status"] == "active":
            CLIENTS[client_id]["last_active"] = time.time()


def update_api(base_url="http://localhost:5000", total_rounds=10, interval=2.0):
    """Update the API with sample metrics."""
    try:
        # Fix base_url if needed
        # Check if this is a Windows machine using 0.0.0.0
        if "0.0.0.0" in base_url and platform.system() == "Windows":
            old_url = base_url
            base_url = base_url.replace("0.0.0.0", "localhost")
            logger.info(f"Detected Windows, changing API URL from {old_url} to {base_url}")
        
        # Check if API is accessible before proceeding
        logger.info(f"Testing connection to metrics API at {base_url}")
        try:
            # Use a simple GET request with a timeout to test connectivity
            response = requests.get(f"{base_url}", timeout=5)
            if response.status_code == 200:
                logger.info(f"Connected to metrics API at {base_url}")
            else:
                logger.warning(f"API returned unexpected status: {response.status_code}, continuing anyway")
        except requests.RequestException as e:
            # Provide more detailed error information
            logger.error(f"Error connecting to API at {base_url}: {e}")
            if "Connection refused" in str(e):
                logger.error("Connection refused - the API server may not be running")
            elif "timed out" in str(e):
                logger.error("Connection timed out - the server may be unreachable")
            elif "NewConnectionError" in str(e):
                logger.error("Unable to establish connection - check your host address")
                logger.error("If using 0.0.0.0 as host, try using localhost instead")
            return
        
        # Initialize metrics store
        metrics_history = []
        
        # Reset metrics first
        logger.info("Resetting metrics")
        try:
            reset_response = requests.post(f"{base_url}/reset", timeout=5)
            if reset_response.status_code == 200:
                logger.info("Reset metrics successfully")
            else:
                logger.warning(f"Failed to reset metrics: {reset_response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Failed to reset metrics: {e}")
            return
        
        # Update system status
        try:
            requests.put(f"{base_url}/system", json=SYSTEM_STATUS, timeout=5)
            logger.info(f"Updated system status")
        except requests.RequestException as e:
            logger.error(f"Failed to update system status: {e}")
            return
        
        # Update initial client information
        try:
            requests.put(f"{base_url}/clients", json=CLIENTS, timeout=5)
            logger.info(f"Updated client information")
        except requests.RequestException as e:
            logger.error(f"Failed to update client information: {e}")
            return
        
        # Update initial network information
        try:
            requests.put(f"{base_url}/network", json=NETWORK)
            logger.info(f"Updated network information")
        except requests.RequestException as e:
            logger.error(f"Failed to update network information: {e}")
            return
        
        # Update initial policy information
        try:
            requests.put(f"{base_url}/policy", json=POLICY)
            logger.info(f"Updated policy information")
        except requests.RequestException as e:
            logger.error(f"Failed to update policy information: {e}")
            return
        
        # Update initial challenges
        try:
            requests.put(f"{base_url}/challenges", json={"active_challenges": ACTIVE_CHALLENGES})
            logger.info(f"Updated challenges")
        except requests.RequestException as e:
            logger.error(f"Failed to update challenges: {e}")
            return
        
        # Simulate rounds
        for round_num in range(1, total_rounds + 1):
            try:
                # Update system status for current round
                SYSTEM_STATUS["current_round"] = round_num
                requests.put(f"{base_url}/system", json=SYSTEM_STATUS)
                
                # Update network metrics
                update_network_metrics(round_num)
                requests.put(f"{base_url}/network", json=NETWORK)
                
                # Update policy metrics
                update_policy_metrics(round_num)
                requests.put(f"{base_url}/policy", json=POLICY)
                
                # Update client status
                update_client_status(round_num)
                requests.put(f"{base_url}/clients", json=CLIENTS)
                
                # Generate metrics for this round
                metrics = generate_metrics(round_num, total_rounds)
                
                # Update current metrics
                requests.put(f"{base_url}/metrics/current", json=metrics)
                
                # Add to history
                metrics_history.append(metrics)
                requests.put(f"{base_url}/metrics/history", json={"history": metrics_history})
                
                logger.info(f"Updated metrics for round {round_num}/{total_rounds}")
                
                # Create snapshot periodically
                if round_num % 3 == 0:
                    try:
                        snapshot_response = requests.post(f"{base_url}/snapshots", 
                                                json={"description": f"Round {round_num} snapshot"})
                        if snapshot_response.status_code == 200:
                            snapshot_id = snapshot_response.json().get("snapshot_id")
                            logger.info(f"Created snapshot {snapshot_id} for round {round_num}")
                    except Exception as e:
                        logger.error(f"Failed to create snapshot: {e}")
                
                # Wait for next update
                time.sleep(interval)
            
            except requests.RequestException as e:
                logger.error(f"API request failed during round {round_num}: {e}")
                logger.info("Continuing with next round...")
                time.sleep(interval)
                continue
        
        # Update system status to completed
        try:
            SYSTEM_STATUS["status"] = "completed"
            requests.put(f"{base_url}/system", json=SYSTEM_STATUS)
            logger.info("Simulation completed")
        except requests.RequestException as e:
            logger.error(f"Failed to update final system status: {e}")
    
    except Exception as e:
        logger.error(f"Error updating API: {e}")
        logger.exception("Exception details:")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate sample metrics for the API")
    parser.add_argument("--api-url", default="http://localhost:5000",
                      help="URL of the metrics API server")
    parser.add_argument("--rounds", type=int, default=10,
                      help="Number of rounds to simulate")
    parser.add_argument("--interval", type=float, default=2.0,
                      help="Update interval in seconds")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()
    
    try:
        # Update API with sample metrics
        update_api(args.api_url, args.rounds, args.interval)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 