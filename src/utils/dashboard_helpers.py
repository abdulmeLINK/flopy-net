# Potential Refactor: This module contains helper functions specifically for the dashboard backend.
# It should be moved to a location within the dashboard's backend codebase, for example:
# dashboard/backend/utils/dashboard_processing.py or dashboard/backend/helpers.py
# This will improve modularity and make it clear that these utilities are not global.

"""
Helper functions for dashboard components
"""

from typing import Dict, Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

def safe_get_metric(data: Dict[str, Any], key: str, default_value: Any = 0) -> Any:
    """
    Safely retrieve a metric from metrics data, handling missing keys.
    
    Args:
        data: The metrics dictionary
        key: The key to retrieve
        default_value: Default value to return if key not found
        
    Returns:
        The value from the dictionary or default if not found
    """
    if not data:
        return default_value
        
    if key in data:
        return data[key]
        
    logger.debug(f"Metric key '{key}' not found in data")
    return default_value
    
def get_network_metrics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and process network metrics, handling missing keys.
    
    Args:
        stats: Raw network statistics
        
    Returns:
        Dictionary with processed metrics
    """
    if not stats:
        return {
            "bandwidth": 0,
            "throughput": 0,
            "latency": 0,
            "packet_loss": 0
        }
    
    # Process the metrics
    bandwidth = safe_get_metric(stats, "bandwidth_mbps", 0)
    throughput = safe_get_metric(stats, "throughput", bandwidth * 0.85)  # Default to ~85% of bandwidth
    latency = safe_get_metric(stats, "latency_ms", 0)
    packet_loss = safe_get_metric(stats, "packet_loss", 0)
    
    return {
        "bandwidth": bandwidth,
        "throughput": throughput,
        "latency": latency,
        "packet_loss": packet_loss
    }

def process_network_data(network_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process network data for display in dashboard.
    
    Args:
        network_data: Raw network data
        
    Returns:
        Processed network data with all required fields
    """
    processed_data = {
        "nodes": [],
        "links": [],
        "metrics": {
            "bandwidth": {"avg": 0, "min": 0, "max": 0},
            "throughput": {"avg": 0, "min": 0, "max": 0},
            "latency": {"avg": 0, "min": 0, "max": 0},
            "packet_loss": {"avg": 0, "min": 0, "max": 0}
        }
    }
    
    # Copy nodes with safe defaults
    for node in network_data.get("nodes", []):
        processed_node = {
            "id": node.get("id", "unknown"),
            "type": node.get("type", "host"),
            "active": node.get("active", True),
            "x": node.get("x", 0),
            "y": node.get("y", 0),
            "cpu": node.get("cpu", 0),
            "memory": node.get("memory", 0)
        }
        processed_data["nodes"].append(processed_node)
    
    # Process links with safe metrics
    total_bw = 0
    total_tp = 0
    total_latency = 0
    total_loss = 0
    min_bw = float('inf')
    max_bw = 0
    min_tp = float('inf')
    max_tp = 0
    min_latency = float('inf')
    max_latency = 0
    min_loss = float('inf')
    max_loss = 0
    
    for link in network_data.get("links", []):
        # Get metrics with safe defaults
        bandwidth = safe_get_metric(link, "bandwidth", 10)
        throughput = safe_get_metric(link, "throughput", bandwidth * 0.85)
        latency = safe_get_metric(link, "latency", 10)
        loss = safe_get_metric(link, "loss", 0)
        
        # Add processed link
        processed_link = {
            "source": link.get("source", "unknown"),
            "target": link.get("target", "unknown"),
            "bandwidth": bandwidth,
            "throughput": throughput,
            "latency": latency,
            "loss": loss,
            "active": link.get("active", True)
        }
        processed_data["links"].append(processed_link)
        
        # Update aggregates
        total_bw += bandwidth
        total_tp += throughput
        total_latency += latency
        total_loss += loss
        
        min_bw = min(min_bw, bandwidth) if min_bw != float('inf') else bandwidth
        max_bw = max(max_bw, bandwidth)
        min_tp = min(min_tp, throughput) if min_tp != float('inf') else throughput
        max_tp = max(max_tp, throughput)
        min_latency = min(min_latency, latency) if min_latency != float('inf') else latency
        max_latency = max(max_latency, latency)
        min_loss = min(min_loss, loss) if min_loss != float('inf') else loss
        max_loss = max(max_loss, loss)
    
    # Calculate averages
    link_count = len(processed_data["links"])
    if link_count > 0:
        processed_data["metrics"]["bandwidth"]["avg"] = total_bw / link_count
        processed_data["metrics"]["bandwidth"]["min"] = min_bw
        processed_data["metrics"]["bandwidth"]["max"] = max_bw
        
        processed_data["metrics"]["throughput"]["avg"] = total_tp / link_count
        processed_data["metrics"]["throughput"]["min"] = min_tp
        processed_data["metrics"]["throughput"]["max"] = max_tp
        
        processed_data["metrics"]["latency"]["avg"] = total_latency / link_count
        processed_data["metrics"]["latency"]["min"] = min_latency
        processed_data["metrics"]["latency"]["max"] = max_latency
        
        processed_data["metrics"]["packet_loss"]["avg"] = total_loss / link_count
        processed_data["metrics"]["packet_loss"]["min"] = min_loss
        processed_data["metrics"]["packet_loss"]["max"] = max_loss
    
    return processed_data 