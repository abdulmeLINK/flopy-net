#!/usr/bin/env python3
"""
Metrics Service Interface

This module defines the interface for the metrics service,
which provides functionality for collecting, storing, and analyzing metrics.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional

class IMetricsService(ABC):
    """
    Interface for metrics service.
    
    The metrics service is responsible for collecting, storing, analyzing,
    and reporting metrics from various components of the system.
    """
    
    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all system metrics.
        
        Returns:
            Dictionary containing a summary of key metrics from all components
        """
        pass
    
    @abstractmethod
    def update_fl_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update federated learning metrics with new data.
        
        Args:
            metrics: Dictionary of metrics to update
        """
        pass
    
    @abstractmethod
    def update_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update system metrics with new data.
        
        Args:
            metrics: Dictionary of system metrics to update
        """
        pass
    
    @abstractmethod
    def update_network_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update network metrics with new data.
        
        Args:
            metrics: Dictionary of network metrics to update
        """
        pass
    
    @abstractmethod
    def get_fl_performance_metrics(self) -> Dict[str, Any]:
        """
        Get federated learning performance metrics.
        
        Returns:
            Dictionary of FL performance metrics like accuracy, loss, etc.
        """
        pass
    
    @abstractmethod
    def get_metric_time_series(self, 
                             metric_key: str, 
                             category: str = "fl",
                             start_time: Optional[float] = None, 
                             end_time: Optional[float] = None) -> List[Tuple[float, Any]]:
        """
        Get a time series for a specific metric.
        
        Args:
            metric_key: Key of the metric to query
            category: Category of metrics (fl, network, system, policy)
            start_time: Start time as Unix timestamp
            end_time: End time as Unix timestamp
            
        Returns:
            List of (timestamp, value) tuples
        """
        pass
    
    @abstractmethod
    def export_metrics_report(self, file_path: str = None, report_format: str = "json") -> bool:
        """
        Export metrics to a report file.
        
        Args:
            file_path: Path to save the report
            report_format: Format of the report (json, csv, txt, html)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def reset_metrics(self) -> None:
        """
        Reset all metrics to their initial state.
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """
        Shutdown the metrics service and perform cleanup.
        """
        pass 