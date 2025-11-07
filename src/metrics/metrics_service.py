#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

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
Metrics Service Implementation.

This module implements the metrics service interface for collecting and managing metrics.
"""

import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import random

from src.core.interfaces.metrics_service import IMetricsService

# Use a lazy import approach for GNS3MetricsExtractor
GNS3_METRICS_AVAILABLE = False
GNS3MetricsExtractor = None

logger = logging.getLogger(__name__)

class MetricsService(IMetricsService):
    """Implementation of the metrics service interface."""
    
    def __init__(self):
        """Initialize the metrics service."""
        self.metrics = {
            "performance": {},
            "network": {},
            "system": {},
            "privacy": {},
            "policy": {},  # Policy metrics category
            "security": {},  # Security metrics category
            "communication": {},  # Communication metrics category
            "resource_consumption": {},  # Resource consumption metrics
            "simulators": {}  # Added for simulator configuration
        }
        self.logs = []
        self.storage_dir = None
        self.start_time = time.time()
        self.metrics_history = {}
        self.last_update_time = {}
        self.max_history_length = 100
        self.gns3_metrics_extractor = None
        
        # Create the metrics directory if it doesn't exist
        os.makedirs("metrics", exist_ok=True)
        
        logger.info("Initialized metrics service")
    
    def check_status(self) -> str:
        """Check the status of the metrics service."""
        # Simple check to verify if the service is operational
        return "operational"
    
    def get_metric(self, category: str, key: str) -> Any:
        """Get a specific metric value.
        
        Args:
            category: Category of the metric (e.g. 'performance', 'network')
            key: Key of the metric
            
        Returns:
            The metric value or None if not found
        """
        if category not in self.metrics:
            return None
            
        if key not in self.metrics[category]:
            return None
            
        metric = self.metrics[category][key]
        if isinstance(metric, dict) and "current" in metric:
            return metric["current"]
        return metric
    
    def get_metrics(self, query=None) -> Dict[str, Any]:
        """Get metrics matching the query.
        
        Args:
            query: Optional query parameters
            
        Returns:
            Dictionary of metrics
        """
        if not query:
            return self.metrics
            
        filtered_metrics = {}
        for category, metrics in self.metrics.items():
            if "category" in query and category != query["category"]:
                continue
                
            filtered_metrics[category] = {}
            for key, value in metrics.items():
                if "key" in query and key != query["key"]:
                    continue
                    
                if "min_value" in query and isinstance(value, dict) and "current" in value:
                    if value["current"] < query["min_value"]:
                        continue
                        
                if "max_value" in query and isinstance(value, dict) and "current" in value:
                    if value["current"] > query["max_value"]:
                        continue
                        
                filtered_metrics[category][key] = value
                
        return filtered_metrics
    
    def configure(self, storage_dir: str) -> None:
        """Configure the metrics service.
        
        Args:
            storage_dir: Directory to store metrics data
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # Load persisted metrics if they exist
        metrics_file = os.path.join(storage_dir, "metrics.json")
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.error(f"Error loading persisted metrics: {e}")
        
        logger.info(f"Configured metrics service with storage directory: {storage_dir}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all system metrics."""
        return self.metrics
    
    def update_fl_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update federated learning metrics with new data."""
        self._update_metrics_category("performance", metrics)
    
    def update_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update system metrics with new data."""
        self._update_metrics_category("system", metrics)
    
    def update_network_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update network metrics with new data."""
        self._update_metrics_category("network", metrics)
    
    def update_security_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update security metrics with new data."""
        self._update_metrics_category("security", metrics)
    
    def update_communication_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update communication metrics with new data."""
        self._update_metrics_category("communication", metrics)
    
    def update_resource_consumption_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update resource consumption metrics with new data."""
        self._update_metrics_category("resource_consumption", metrics)
    
    def get_fl_performance_metrics(self) -> Dict[str, Any]:
        """Get federated learning performance metrics."""
        return self.metrics.get("performance", {})
    
    def get_metric_time_series(self, 
                             metric_key: str, 
                             category: str = "fl",
                             start_time: Optional[float] = None, 
                             end_time: Optional[float] = None) -> List[Tuple[float, Any]]:
        """Get a time series for a specific metric."""
        if category not in self.metrics:
            return []
            
        if metric_key not in self.metrics[category]:
            return []
            
        # Get metric history
        history = self.metrics[category][metric_key].get("history", [])
        
        # Filter by time range if specified
        if start_time is not None or end_time is not None:
            filtered_history = []
            for entry in history:
                timestamp = entry.get("timestamp", 0)
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                filtered_history.append((timestamp, entry.get("value")))
            return filtered_history
            
        return [(entry.get("timestamp", 0), entry.get("value")) for entry in history]
    
    def export_metrics_report(self, file_path: str = None, report_format: str = "json") -> bool:
        """Export metrics to a report file."""
        try:
            if file_path is None and self.storage_dir:
                # Generate default file path in storage directory
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(self.storage_dir, f"metrics_report_{timestamp}.{report_format}")
            
            if not file_path:
                logger.error("No file path specified and no storage directory configured")
                return False
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Export based on format
            if report_format == "json":
                with open(file_path, 'w') as f:
                    json.dump(self.metrics, f, indent=2)
            else:
                logger.error(f"Unsupported report format: {report_format}")
                return False
            
            logger.info(f"Exported metrics report to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting metrics report: {e}")
            return False
    
    def reset_metrics(self) -> None:
        """Reset all metrics to their initial state."""
        self.metrics = {
            "performance": {},
            "network": {},
            "system": {},
            "privacy": {},
            "policy": {},
            "security": {},
            "communication": {},
            "resource_consumption": {},
            "simulators": {}
        }
        self.logs = []
        self.metrics_history = {}
        self.last_update_time = {}
        logger.info("Reset all metrics")
    
    def shutdown(self) -> None:
        """Shutdown the metrics service and perform cleanup."""
        if self.storage_dir:
            # Export final metrics report
            self.export_metrics_report()
            
            # Save current metrics state
            metrics_file = os.path.join(self.storage_dir, "metrics.json")
            try:
                with open(metrics_file, "w") as f:
                    json.dump(self.metrics, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving metrics state: {e}")
                
        logger.info("Metrics service shutdown complete")
    
    def log_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Log a metric with the given name, value, and tags.
        
        Args:
            name: Name of the metric
            value: Value of the metric
            tags: Optional tags to associate with the metric
        """
        try:
            # Parse the metric name to determine category
            parts = name.split('.')
            
            # Default category is 'performance' if not specified in the name
            if len(parts) > 1:
                # Use first part as category, rest as name
                category = parts[0]
                metric_name = '.'.join(parts[1:])
            else:
                category = "performance"
                metric_name = name
            
            # Record the metric
            self.record_metric(category, metric_name, value, tags)
            
        except Exception as e:
            logger.error(f"Error logging metric '{name}': {e}")
    
    def _update_metrics_category(self, category: str, metrics: Dict[str, Any]) -> None:
        """Update a specific metrics category with new data."""
        if category not in self.metrics:
            self.metrics[category] = {}
            
        for key, value in metrics.items():
            # Store the current value and history if not present
            if key not in self.metrics[category]:
                self.metrics[category][key] = {
                    "current": value,
                    "history": []
                }
                
                # Add the first history point
                self.metrics[category][key]["history"].append({
                    "timestamp": time.time(),
                    "value": value
                })
            else:
                # Update the current value
                self.metrics[category][key]["current"] = value
                
                # Add to history
                self.metrics[category][key]["history"].append({
                    "timestamp": time.time(),
                    "value": value
                })
                
                # Limit history length
                history = self.metrics[category][key]["history"]
                if len(history) > self.max_history_length:
                    self.metrics[category][key]["history"] = history[-self.max_history_length:]
                    
        # Update last update time
        self.last_update_time[category] = time.time()
        
    def log_event(self, event_type: str, message: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Log an event with the given type, message, and tags.
        
        Args:
            event_type: Type of the event
            message: Event message
            tags: Optional tags to associate with the event
        """
        log_entry = {
            "timestamp": time.time(),
            "type": event_type,
            "message": message,
            "tags": tags or {}
        }
        
        self.logs.append(log_entry)
        logger.info(f"Logged event: {event_type} - {message}")
        
        # Limit logs length
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
            
    def get_logs(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get logs matching the query.
        
        Args:
            query: Optional query parameters
            
        Returns:
            List of log entries
        """
        if not query:
            return self.logs
            
        filtered_logs = []
        for log in self.logs:
            # Filter by type
            if "type" in query and log["type"] != query["type"]:
                continue
                
            # Filter by time range
            if "start_time" in query and log["timestamp"] < query["start_time"]:
                continue
                
            if "end_time" in query and log["timestamp"] > query["end_time"]:
                continue
                
            # Filter by tags
            if "tags" in query:
                tags_match = True
                for tag_key, tag_value in query["tags"].items():
                    if tag_key not in log["tags"] or log["tags"][tag_key] != tag_value:
                        tags_match = False
                        break
                        
                if not tags_match:
                    continue
                    
            filtered_logs.append(log)
            
        return filtered_logs
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get the latest metrics for all categories."""
        # Log warning if no metrics are available
        if not any(self.metrics.values()):
            logger.warning("No metrics data available. Use update_*_metrics() methods to add real data.")
        
        return self.metrics
    
    def get_fl_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        # Log warning if no system metrics are available
        if not self.metrics.get("system"):
            logger.warning("No system metrics available. Use update_system_metrics() to add real data.")
            
        return self.metrics.get("system", {})
    
    def get_fl_network_metrics(self) -> Dict[str, Any]:
        """Get network metrics."""
        # Log warning if no network metrics are available
        if not self.metrics.get("network"):
            logger.warning("No network metrics available. Use update_network_metrics() to add real data.")
            
        return self.metrics.get("network", {})
    
    def get_fl_model_metrics(self) -> Dict[str, Any]:
        """Get model metrics."""
        # Log warning if no performance metrics are available
        if not self.metrics.get("performance"):
            logger.warning("No model metrics available. Use update_fl_metrics() to add real data.")
            
        return self.metrics.get("performance", {})
    
    def get_fl_policy_metrics(self) -> Dict[str, Any]:
        """Get policy metrics."""
        # Log warning if no policy metrics are available
        if not self.metrics.get("policy"):
            logger.warning("No policy metrics available. Use update_policy_metrics() to add real data.")
            
        return self.metrics.get("policy", {})
    
    def get_fl_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        # Log warning if no security metrics are available
        if not self.metrics.get("security"):
            logger.warning("No security metrics available. Use update_security_metrics() to add real data.")
            
        return self.metrics.get("security", {})
    
    def get_fl_communication_metrics(self) -> Dict[str, Any]:
        """Get communication metrics."""
        # Log warning if no communication metrics are available
        if not self.metrics.get("communication"):
            logger.warning("No communication metrics available. Use update_communication_metrics() to add real data.")
            
        return self.metrics.get("communication", {})
    
    def get_fl_resource_consumption_metrics(self) -> Dict[str, Any]:
        """Get resource consumption metrics."""
        # Log warning if no resource consumption metrics are available
        if not self.metrics.get("resource_consumption"):
            logger.warning("No resource consumption metrics available. Use update_resource_consumption_metrics() to add real data.")
            
        return self.metrics.get("resource_consumption", {})
    
    def update_policy_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update policy engine metrics with new data."""
        self._update_metrics_category("policy", metrics)
    
    def get_metric_history(self, category: str, name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history for a specific metric.
        
        Args:
            category: Category of the metric
            name: Name of the metric
            limit: Maximum number of history points to return
            
        Returns:
            List of history points
        """
        if category not in self.metrics:
            return []
            
        if name not in self.metrics[category]:
            return []
            
        metric = self.metrics[category][name]
        if "history" not in metric:
            return []
            
        history = metric["history"]
        
        # Return most recent points first
        return sorted(history, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
    
    def record_event(self, category: str, name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record an event.
        
        Args:
            category: Category of the event
            name: Name of the event
            details: Optional details of the event
        """
        try:
            timestamp = time.time()
            
            event = {
                "timestamp": timestamp,
                "category": category,
                "name": name,
                "details": details or {}
            }
            
            # Add to logs
            self.logs.append(event)
            
            # Trim logs if too long
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]
                
            # Log to logger
            log_message = f"Event: {category}.{name}"
            if details:
                log_message += f" - {json.dumps(details)}"
                
            logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Error recording event '{category}.{name}': {e}")
    
    def initialize_gns3_metrics_extractor(self, host: str = "localhost", 
                                        port: int = 3080,
                                        project_id: Optional[str] = None):
        """Initialize a GNS3 metrics extractor to collect network metrics.
        
        Args:
            host: GNS3 server host
            port: GNS3 server port
            project_id: Optional GNS3 project ID
            
        Returns:
            True if successful, False otherwise
        """
        # Use lazy import to avoid circular dependencies
        global GNS3MetricsExtractor, GNS3_METRICS_AVAILABLE
        
        if GNS3MetricsExtractor is None:
            try:
                from src.dashboard.components.gns3_metrics_extractor import GNS3MetricsExtractor as Extractor
                GNS3MetricsExtractor = Extractor
                GNS3_METRICS_AVAILABLE = True
            except ImportError:
                logger.error("GNS3 metrics extractor not available")
                GNS3_METRICS_AVAILABLE = False
            
        if not GNS3_METRICS_AVAILABLE:
            logger.error("GNS3 metrics extractor not available")
            return False
            
        try:
            # Initialize extractor
            self.gns3_metrics_extractor = GNS3MetricsExtractor(host, port, project_id)
            
            # Test connection
            if self.gns3_metrics_extractor.test_connection():
                logger.info(f"Successfully connected to GNS3 server at {host}:{port}")
                
                # If project ID wasn't provided, try to get the active project
                if not project_id:
                    project_list = self.gns3_metrics_extractor.get_projects()
                    if project_list and len(project_list) > 0:
                        # Use the first project
                        self.gns3_metrics_extractor.project_id = project_list[0].get("project_id")
                        logger.info(f"Using GNS3 project: {project_list[0].get('name')} ({self.gns3_metrics_extractor.project_id})")
                
                return True
            else:
                logger.error(f"Failed to connect to GNS3 server at {host}:{port}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing GNS3 metrics extractor: {e}")
            return False
    
    def get_network_metrics(self, metric_type: str = "all", 
                            force_update: bool = False) -> Dict[str, Any]:
        """
        Get network metrics from GNS3 or from stored metrics.
        
        Args:
            metric_type: Type of metrics to get (all, nodes, links, etc.)
            force_update: Whether to force an update
            
        Returns:
            Dictionary of network metrics
        """
        # If no GNS3 extractor is available, return empty metrics and log warning
        if not self.gns3_metrics_extractor:
            logger.warning("No GNS3 metrics extractor available. Use initialize_gns3_metrics_extractor() first.")
            return self.metrics.get("network", {})
            
        try:
            # Check if we need to update metrics
            last_update = self.last_update_time.get("network", 0)
            current_time = time.time()
            
            # Only update if forced or it's been more than 10 seconds
            if force_update or current_time - last_update > 10:
                if metric_type == "all" or metric_type == "nodes":
                    # Get node metrics
                    nodes = self.gns3_metrics_extractor.get_nodes()
                    
                    if nodes:
                        node_metrics = {
                            "nodes": {
                                "total": len(nodes),
                                "active": sum(1 for node in nodes if node.get("status") == "started"),
                                "by_type": {}
                            }
                        }
                        
                        # Count by type
                        for node in nodes:
                            node_type = node.get("node_type", "other")
                            if node_type not in node_metrics["nodes"]["by_type"]:
                                node_metrics["nodes"]["by_type"][node_type] = 0
                                
                            node_metrics["nodes"]["by_type"][node_type] += 1
                            
                        self._update_metrics_category("network", node_metrics)
                        
                if metric_type == "all" or metric_type == "links":
                    # Get link metrics
                    links = self.gns3_metrics_extractor.get_links()
                    
                    if links:
                        link_metrics = {
                            "links": {
                                "total": len(links),
                                "active": sum(1 for link in links if link.get("status") != "down")
                            }
                        }
                        
                        self._update_metrics_category("network", link_metrics)
                
                # Update the last update time
                self.last_update_time["network"] = current_time
                        
            # Return the current network metrics
            return self.metrics.get("network", {})
                
        except Exception as e:
            logger.error(f"Error getting GNS3 network metrics: {e}")
            # Return existing metrics in case of error rather than generating mock data
            return self.metrics.get("network", {})
    
    def set_simulator_config(self, simulator_type: str, config: Dict[str, Any]) -> None:
        """
        Store simulator configuration for use in metrics and simulations.
        
        Args:
            simulator_type: Type of simulator (e.g., 'gns3', 'mininet')
            config: Configuration parameters for the simulator
        """
        try:
            # Initialize simulator config storage if not already present
            if "simulators" not in self.metrics:
                self.metrics["simulators"] = {}
                
            # Store the simulator configuration
            self.metrics["simulators"][simulator_type] = {
                "config": config,
                "timestamp": time.time(),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Record event
            self.record_event(
                category="simulators",
                name="simulator_configured",
                details={
                    "simulator_type": simulator_type,
                    "config_summary": {
                        "topology": config.get("topology", {}).get("type", "unknown"),
                        "network_challenges": config.get("network_challenges", {}).get("intensity", "none"),
                        "timestamp": time.time()
                    }
                }
            )
            
            logger.info(f"Stored configuration for {simulator_type} simulator")
            
            # If storage directory exists, persist the updated configuration
            if self.storage_dir:
                config_file = os.path.join(self.storage_dir, f"{simulator_type}_simulator_config.json")
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Persisted {simulator_type} simulator configuration to {config_file}")
                
            return True
        except Exception as e:
            logger.error(f"Error storing simulator configuration: {e}")
            return False
            
    def get_simulator_config(self, simulator_type: str = None) -> Dict[str, Any]:
        """
        Get stored simulator configuration.
        
        Args:
            simulator_type: Optional simulator type to retrieve specific config
            
        Returns:
            Dictionary with simulator configuration(s)
        """
        if "simulators" not in self.metrics:
            return {}
            
        if simulator_type:
            return self.metrics["simulators"].get(simulator_type, {}).get("config", {})
        else:
            # Return all simulator configurations
            return {
                sim_type: sim_data.get("config", {})
                for sim_type, sim_data in self.metrics["simulators"].items()
            }
    
    def record_metric(self, category: str, name: str, value: Any, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value with optional tags.
        
        Args:
            category: Category of the metric (e.g. 'performance', 'network')
            name: Name of the metric
            value: Value of the metric
            tags: Optional tags to associate with the metric
        """
        try:
            # Ensure value is numeric for calculations
            numeric_value = value
            if isinstance(value, str):
                try:
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    # If we can't convert to float, store as is but don't perform calculations
                    logger.warning(f"Non-numeric value '{value}' provided for metric '{category}.{name}'")
                    
                    # Initialize category if it doesn't exist
                    if category not in self.metrics:
                        self.metrics[category] = {}
                        
                    # Store string value without calculations
                    if name not in self.metrics[category]:
                        self.metrics[category][name] = {
                            "current": value,
                            "history": [],
                            "tags": tags or {}
                        }
                    else:
                        self.metrics[category][name]["current"] = value
                        
                    # Add history point
                    timestamp = time.time()
                    history_point = {
                        "timestamp": timestamp,
                        "value": value
                    }
                    
                    if tags:
                        history_point["tags"] = tags
                        
                    # Initialize metrics_history if needed
                    if category not in self.metrics_history:
                        self.metrics_history[category] = {}
                        
                    if name not in self.metrics_history[category]:
                        self.metrics_history[category][name] = []
                        
                    # Add to history
                    self.metrics_history[category][name].append(history_point)
                    
                    # Add to metric history within the metric object
                    if "history" not in self.metrics[category][name]:
                        self.metrics[category][name]["history"] = []
                        
                    self.metrics[category][name]["history"].append(history_point)
                    
                    # Update last update time
                    self.last_update_time[category] = timestamp
                    
                    return
            
            # Initialize category if it doesn't exist
            if category not in self.metrics:
                self.metrics[category] = {}
                
            # Initialize metric if it doesn't exist
            if name not in self.metrics[category]:
                self.metrics[category][name] = {
                    "current": numeric_value,
                    "min": numeric_value,
                    "max": numeric_value,
                    "avg": numeric_value,
                    "count": 1,
                    "history": [],
                    "tags": tags or {}
                }
            else:
                metric = self.metrics[category][name]
                current_count = metric.get("count", 1)
                
                # Update current value
                metric["current"] = numeric_value
                
                # Update min/max
                metric["min"] = min(metric.get("min", float('inf')), numeric_value)
                metric["max"] = max(metric.get("max", float('-inf')), numeric_value)
                
                # Update average
                metric["avg"] = (metric.get("avg", 0) * current_count + numeric_value) / (current_count + 1)
                
                # Update count
                metric["count"] = current_count + 1
                
                # Update tags
                if tags:
                    metric_tags = metric.get("tags", {})
                    metric_tags.update(tags)
                    metric["tags"] = metric_tags
                    
            # Add history point
            timestamp = time.time()
            history_point = {
                "timestamp": timestamp,
                "value": numeric_value
            }
            
            if tags:
                history_point["tags"] = tags
                
            # Initialize metrics_history if needed
            if category not in self.metrics_history:
                self.metrics_history[category] = {}
                
            if name not in self.metrics_history[category]:
                self.metrics_history[category][name] = []
                
            # Add to history
            self.metrics_history[category][name].append(history_point)
            
            # Add to metric history within the metric object
            if "history" not in self.metrics[category][name]:
                self.metrics[category][name]["history"] = []
                
            self.metrics[category][name]["history"].append(history_point)
            
            # Trim history if too long
            if len(self.metrics[category][name]["history"]) > self.max_history_length:
                self.metrics[category][name]["history"] = self.metrics[category][name]["history"][-self.max_history_length:]
                
            # Update last update time
            self.last_update_time[category] = timestamp
            
        except Exception as e:
            logger.error(f"Error recording metric '{category}.{name}': {e}") 