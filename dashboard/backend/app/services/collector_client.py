import httpx
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from ..core.config import settings
from ..models.collector_models import (
    MetricsResponse, LatestMetricResponse, FLMetricsResponse,
    PolicyDecisionsResponse, MonitoringStatus
)
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class CollectorApiClient:
    """Client for interacting with the Collector API."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the client with the Collector API base URL.
        
        Args:
            base_url: The base URL for the Collector API. Defaults to the URL in settings.
        """
        self.base_url = base_url or settings.COLLECTOR_URL
        # Use configurable timeouts instead of hardcoded values
        self.timeout = httpx.Timeout(
            connect=settings.HTTP_CONNECT_TIMEOUT,
            read=settings.HTTP_READ_TIMEOUT,
            write=settings.HTTP_WRITE_TIMEOUT,
            pool=settings.HTTP_POOL_TIMEOUT
        )
        self.limits = httpx.Limits(
            max_keepalive_connections=settings.MAX_KEEPALIVE_CONNECTIONS,
            max_connections=settings.MAX_CONNECTIONS,
            keepalive_expiry=settings.KEEPALIVE_EXPIRY
        )
        
        # Add basic authentication for collector API
        auth = httpx.BasicAuth("admin", "securepassword")
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url, 
            timeout=self.timeout,
            limits=self.limits,
            follow_redirects=True,
            auth=auth
        )
        
        logging.info(f"Initialized Collector API client with base URL: {self.base_url}")

    def set_base_url(self, base_url: str):
        """Update the base URL for the client."""
        if self.base_url != base_url:
            self.base_url = base_url.rstrip('/')
            
            # Add basic authentication for collector API
            auth = httpx.BasicAuth("admin", "securepassword")
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url, 
                timeout=self.timeout,
                limits=self.limits,
                auth=auth
            )
            logging.info(f"Updated Collector API client base URL to: {self.base_url}")

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
        logging.info("Closed Collector API client.")
        
    async def aclose(self):
        """Alias for close() to maintain compatibility with code that expects aclose()."""
        await self.close()

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        custom_timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Collector API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON data for POST/PUT requests
            custom_timeout: Override default timeout for specific requests
            
        Returns:
            API response as a dict
            
        Raises:
            httpx.HTTPStatusError: For non-2xx responses
            httpx.RequestError: For request errors (e.g., connection errors)
            httpx.TimeoutException: For timeout errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Use custom timeout if provided, otherwise use client timeout
        timeout = custom_timeout if custom_timeout else self.timeout
        
        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()

    async def get_health(self) -> Dict[str, Any]:
        """Check the health of the Collector API."""
        resp = await self._client.get("/health", timeout=10.0)
        resp.raise_for_status()
        logging.info(f"Successfully connected to collector health endpoint at {self.base_url}")
        return resp.json()

    async def test_connection(self) -> bool:
        """Test the connection to the collector API."""
        try:
            health = await self.get_health()
            return "error" not in health
        except Exception:
            return False
    
    async def get_api_docs(self) -> Dict[str, Any]:
        """Get the API documentation from the Collector."""
        return await self._make_request("GET", "/")
    
    async def get_all_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        type_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_desc: bool = True
    ) -> MetricsResponse:
        """
        Get all metrics with optional filtering.
        
        Args:
            start_time: Start time for filtering (ISO format)
            end_time: End time for filtering (ISO format)
            type_filter: Filter by metric type (e.g., "fl_server", "policy_engine", "network")
            limit: Maximum number of results
            offset: Pagination offset
            sort_desc: Sort by timestamp descending if True, ascending if False
            
        Returns:
            Metrics response
        """
        params = {
            "start": start_time,
            "end": end_time,
            "type": type_filter,
            "limit": limit,
            "offset": offset,
            "sort_desc": str(sort_desc).lower()
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        data = await self._make_request("GET", "/api/metrics", params=params)
        return MetricsResponse(**data)
    
    async def get_latest_metrics(self, type_filter: Optional[str] = None) -> Union[LatestMetricResponse, Dict[str, Any]]:
        """
        Get the latest metrics snapshot with optimized error handling.
        
        Args:
            type_filter: Filter by metric type
            
        Returns:
            Latest metrics response or fallback data if failed
        """
        params = {}
        if type_filter:
            params["type"] = type_filter
            
        try:
            # Use the existing client with connection pooling
            response = await self._client.get("/api/metrics/latest", params=params)
            
            # Handle 404 for network metrics gracefully
            if response.status_code == 404:
                logger.warning(f"Metrics endpoint not found for type: {type_filter}")
                return self._get_fallback_metrics(type_filter)
                
            response.raise_for_status()
            
            # For FL server type, return the response directly
            if type_filter == "fl_server":
                return response.json()
            
            # For other types, wrap in LatestMetricResponse format
            data = response.json()
            return LatestMetricResponse(**data) if isinstance(data, dict) and "metrics" in data else LatestMetricResponse(metrics=data, timestamp=datetime.now().isoformat())
                
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout fetching latest metrics (type={type_filter}): {e}")
            return self._get_fallback_metrics(type_filter)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Metrics endpoint not found for type: {type_filter}")
                return self._get_fallback_metrics(type_filter)
            logger.error(f"HTTP error fetching latest metrics (type={type_filter}): {e}")
            return self._get_fallback_metrics(type_filter)
        except Exception as e:
            logger.error(f"Error fetching latest metrics (type={type_filter}): {e}")
            return self._get_fallback_metrics(type_filter)
    
    def _get_fallback_metrics(self, type_filter: Optional[str] = None) -> Union[LatestMetricResponse, Dict[str, Any]]:
        """Get fallback metrics when the real metrics are unavailable"""
        if type_filter == "fl_server":
            return {
                "round": 0,
                "status": "disconnected",
                "accuracy": 0.0,
                "loss": 0.0,
                "clients": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # Default fallback for network and other types
        return LatestMetricResponse(
            metrics={
                "node_count": 0,
                "link_count": 0,
                "avg_latency_ms": 0,
                "packet_loss_percent": 0,
                "bandwidth_utilization_percent": 0,
                "sdn_status": "unknown",
                "switches_count": 0,
                "total_flows": 0,
                "node_statuses": {"started": 0, "stopped": 0}
            },
            timestamp=datetime.now().isoformat()
        )

    async def get_fl_metrics(
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Get FL metrics from the collector.
        
        Args:
            params: Additional query parameters
            limit: Maximum number of metrics to return (uses configurable default)
            
        Returns:
            Full collector response dict with 'metrics' field
        """
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE
        limit = min(limit, settings.MAX_PAGE_SIZE)
        
        query_params = {"limit": limit}
        if params:
            query_params.update(params)
        
        # Fixed endpoint URL to match collector API and return full response
        return await self._make_request("GET", "/api/metrics/fl", params=query_params)
    
    async def get_policy_decisions(
        self, 
        params: Optional[Dict[str, Any]] = None,
        limit: int = None
    ) -> PolicyDecisionsResponse:
        """
        Get policy decisions from the collector.
        
        Args:
            params: Additional query parameters 
            limit: Maximum number of decisions to return (uses configurable default)
        """
        # Use configurable default limit instead of hardcoded value  
        if limit is None:
            limit = settings.DEFAULT_EVENTS_LIMIT
        limit = min(limit, settings.MAX_PAGE_SIZE)
        
        query_params = {"limit": limit}
        if params:
            query_params.update(params)
        
        return await self._make_request("GET", "/api/policy/decisions", params=query_params)
    
    async def get_events(
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Get events from the collector.
        
        Args:
            params: Additional query parameters
            limit: Maximum number of events to return (uses configurable default)
        """
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.DEFAULT_EVENTS_LIMIT
        limit = min(limit, settings.MAX_PAGE_SIZE)
        
        query_params = {
            "limit": limit,
        }
        if params:
            query_params.update(params)
        
        return await self._make_request("GET", "/api/events", params=query_params)
    
    async def get_events_data(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get events data from the collector.
        
        Args:
            limit: Maximum number of events to return (uses configurable default)
        """
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE
        limit = min(limit, settings.MAX_PAGE_SIZE)
        
        return await self._make_request("GET", "/api/events/data", params={"limit": limit})

    async def get_policy_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> MetricsResponse:
        """Get policy engine metrics."""
        params = {
            "start": start_time,
            "end": end_time,
            "limit": limit,
            "type": "policy_engine"
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        data = await self._make_request("GET", "/api/metrics", params=params)
        return MetricsResponse(**data)

    async def get_metrics(
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all metrics from the collector.
        
        Args:
            params: Additional query parameters
            limit: Maximum number of metrics to return (uses configurable default)
            start_time: Start time for filtering (ISO format)
            end_time: End time for filtering (ISO format)
        """
        query_params = {}
        
        if params:
            query_params.update(params)
            
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.DEFAULT_PAGE_SIZE
        query_params["limit"] = min(limit, settings.MAX_PAGE_SIZE)
        
        if start_time:
            query_params["start_time"] = start_time
        if end_time:
            query_params["end_time"] = end_time
        
        return await self._make_request("GET", "/api/metrics", params=query_params)

    async def get_network_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> MetricsResponse:
        """Get network metrics."""
        params = {
            "start": start_time,
            "end": end_time,
            "limit": limit,
            "type": "network"
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        data = await self._make_request("GET", "/api/metrics", params=params)
        return MetricsResponse(**data)

    async def get_metrics_time_range(
        self,
        start_time: str,
        end_time: str,
        type_filter: Optional[str] = None
    ) -> MetricsResponse:
        """Get metrics for a specific time range."""
        params = {
            "start": start_time,
            "end": end_time,
            "type": type_filter,
            "limit": 500
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        data = await self._make_request("GET", "/api/metrics", params=params)
        return MetricsResponse(**data)

    async def get_system_events(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        source_component: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get system events - returns raw response without model validation."""
        params = {
            "start": start_time,
            "end": end_time,
            "source_component": source_component,
            "event_type": event_type,
            "limit": limit,
            "offset": offset
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            # Get raw response without model parsing to avoid validation errors
            response_data = await self._make_request("GET", "/api/events", params=params)
            
            # Return the raw response data - don't try to parse through EventsResponse model
            # since the collector events don't have all required fields like event_id
            return response_data
        except Exception as e:
            logger.error(f"Error fetching system events: {e}")
            # Return safe empty response structure
            return {
                "events": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    async def get_events_summary(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get events summary."""
        return await self._make_request("GET", "/api/events/summary", params=params)

    async def get_monitoring_status(self) -> MonitoringStatus:
        """Get monitoring status."""
        data = await self._make_request("GET", "/api/monitoring/status")
        return MonitoringStatus(**data)

    async def query_metrics_complex(self, query_body: Dict[str, Any]) -> Dict[str, Any]:
        """Query metrics with complex parameters."""
        return await self._make_request("POST", "/api/metrics/query", json_data=query_body)

    async def get_fl_summary_fast(self, limit: int = None) -> Dict[str, Any]:
        """
        Get FL summary data optimized for fast dashboard loading.
        
        Args:
            limit: Maximum number of data points (uses configurable default)
            
        Returns:
            FL summary data
        """
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.DEFAULT_EVENTS_LIMIT
        limit = min(limit, settings.MAX_FL_ROUNDS_LIMIT)
        
        params = {
            "include_summary": "true",
            "limit": limit
        }
        
        try:
            return await self._make_request("GET", "/api/metrics/fl/summary", params=params, custom_timeout=30.0)
        except Exception as e:
            logger.error(f"Error fetching FL summary: {e}")
            return {
                "error": str(e),
                "latest_accuracy": 0.0,
                "latest_loss": 0.0,
                "total_rounds": 0,
                "status": "error"
            }

    async def get_fl_chart_data(self, limit: int = None, include_details: bool = False) -> Dict[str, Any]:
        """
        Get FL data optimized for dashboard charts.
        
        Args:
            limit: Maximum number of data points (uses configurable default)
            include_details: Whether to include detailed metrics
            
        Returns:
            Chart-optimized FL data
        """
        # Use configurable default limit instead of hardcoded value
        if limit is None:
            limit = settings.MAX_PAGE_SIZE
        limit = min(limit, settings.MAX_FL_ROUNDS_LIMIT)
        
        params = {
            "limit": limit,
            "include_details": str(include_details).lower()
        }
        
        try:
            return await self._make_request("GET", "/api/metrics/fl/chart-data", params=params, custom_timeout=30.0)
        except Exception as e:
            logger.error(f"Error fetching FL chart data: {e}")
            return {
                "error": str(e),
                "rounds": [],
                "total": 0
            }

    async def get_fl_status(self) -> Dict[str, Any]:
        """
        Get current FL training status.
        
        Returns:
            FL status response with current training state
        """
        try:
            return await self._make_request("GET", "/api/metrics/fl/status", custom_timeout=10.0)
        except Exception as e:
            logger.error(f"Error fetching FL status: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "training_active": False,
                "current_round": 0,
                "latest_accuracy": 0.0,
                "latest_loss": 0.0,
                "connected_clients": 0,
                "training_complete": False,
                "fl_server_available": False
            }

    async def get_fl_rounds(self, limit: int = None) -> Dict[str, Any]:
        """Get FL rounds data from the collector using the enhanced FL rounds endpoint."""
        params = {}
        if limit:
            params["limit"] = limit
            
        try:
            return await self._make_request("GET", "/api/metrics/fl/rounds", params=params)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting FL rounds: {e.response.status_code}")
            return {"error": f"HTTP {e.response.status_code}", "rounds": []}
        except Exception as e:
            logger.error(f"Error getting FL rounds: {e}")
            return {"error": str(e), "rounds": []}

    async def get_fl_configuration(self) -> Dict[str, Any]:
        """
        Get comprehensive FL configuration from the collector including:
        - FL server configuration (model, dataset, rounds)
        - Policy engine parameters  
        - Training hyperparameters
        - Model configuration
        - Federation settings
        """
        try:
            logger.info("CollectorApiClient: Fetching FL configuration from /api/metrics/fl/config")
            
            # Use a longer timeout for config requests as they may query multiple sources
            config_data = await self._make_request("GET", "/api/metrics/fl/config", custom_timeout=15.0)
            
            logger.info(f"CollectorApiClient: Successfully retrieved FL configuration with status: {config_data.get('status', 'unknown')}")
            logger.debug(f"FL config data sources: {config_data.get('data_sources', [])}")
            
            return config_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting FL configuration: {e.response.status_code}")
            if e.response.status_code == 404:
                return {"error": "FL configuration endpoint not available", "status": "endpoint_not_found"}
            elif e.response.status_code == 503:
                return {"error": "FL configuration service unavailable", "status": "service_unavailable"}
            else:
                return {"error": f"HTTP {e.response.status_code}", "status": "http_error"}
        except httpx.TimeoutException:
            logger.error("Timeout getting FL configuration")
            return {"error": "Request timeout", "status": "timeout"}
        except Exception as e:
            logger.error(f"Error getting FL configuration: {e}")
            return {"error": str(e), "status": "error"}

    async def get_network_topology(
        self,
        source: str = "all",
        include_metrics: bool = True,
        format_type: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Get detailed network topology data from GNS3 and SDN controller.
        
        Args:
            source: Data source ('all', 'gns3', 'sdn')
            include_metrics: Include performance metrics
            format_type: Response format ('detailed', 'summary')
            
        Returns:
            Network topology response
        """
        try:
            params = {
                "source": source,
                "include_metrics": str(include_metrics).lower(),
                "format": format_type
            }
            logger.info(f"CollectorApiClient: Fetching network topology with source={source}, format={format_type}")
            return await self._make_request("GET", "/api/network/topology", params=params)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting network topology: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "nodes": [],
                "links": [],
                "switches": [],
                "hosts": [],
                "statistics": {
                    "total_nodes": 0,
                    "total_links": 0,
                    "total_switches": 0,
                    "total_hosts": 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting network topology: {e}")
            return {
                "error": str(e),
                "nodes": [],
                "links": [],
                "switches": [],
                "hosts": [],
                "statistics": {
                    "total_nodes": 0,
                    "total_links": 0,
                    "total_switches": 0,
                    "total_hosts": 0
                }
            }

    async def get_live_network_topology(self) -> Dict[str, Any]:
        """
        Get live network topology data with real-time updates.
        
        Returns:
            Live network topology response
        """
        try:
            logger.info("CollectorApiClient: Fetching live network topology")
            return await self._make_request("GET", "/api/network/topology/live")
        except Exception as e:
            logger.error(f"Error getting live network topology: {e}")
            raise

    async def get_network_flows(self) -> Dict[str, Any]:
        """
        Get network flows from the collector service.
        
        Returns:
            Network flows response from collector
        """
        try:
            logger.info("CollectorApiClient: Fetching network flows")
            return await self._make_request("GET", "/api/network/flows")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting network flows: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "flows": [],
                "summary": {
                    "total_flows": 0,
                    "switches_with_flows": 0,
                    "table_stats": {}
                }
            }
        except Exception as e:
            logger.error(f"Error getting network flows: {e}")
            return {
                "error": str(e),
                "flows": [],
                "summary": {
                    "total_flows": 0,
                    "switches_with_flows": 0,
                    "table_stats": {}
                }
            }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive network performance metrics with health scoring.
        
        Returns:
            Performance metrics response from collector including:
            - Real-time bandwidth, latency, and packet statistics  
            - Network health score (0-100)
            - Port statistics with error rates
            - Performance trends and aggregations
        """
        try:
            logger.info("CollectorApiClient: Fetching performance metrics")
            return await self._make_request("GET", "/api/performance/metrics")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting performance metrics: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "network_health": {
                    "score": 0,
                    "status": "error"
                },
                "latency": {"average": 0, "minimum": 0, "maximum": 0},
                "bandwidth": {"average": 0, "minimum": 0, "maximum": 0},
                "port_statistics": {}
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                "error": str(e),
                "network_health": {
                    "score": 0,
                    "status": "error"
                },
                "latency": {"average": 0, "minimum": 0, "maximum": 0},
                "bandwidth": {"average": 0, "minimum": 0, "maximum": 0},
                "port_statistics": {}
            }

    async def get_flow_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive flow statistics with efficiency calculations.
        
        Returns:
            Flow statistics response from collector including:
            - Flow distribution by priority, table, and type
            - Match criteria and action statistics  
            - Flow efficiency metrics
            - Bandwidth utilization per flow
        """
        try:
            logger.info("CollectorApiClient: Fetching flow statistics")
            return await self._make_request("GET", "/api/flows/statistics")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting flow statistics: {e.response.status_code}")
            return {
                "error": f"HTTP {e.response.status_code}",
                "flow_statistics": {
                    "total_flows": 0,
                    "active_flows": 0,
                    "flows_per_switch": {},
                    "priority_distribution": {},
                    "table_distribution": {}
                },
                "utilization_metrics": {
                    "efficiency_percentage": 0,
                    "efficiency_rating": "poor"
                }
            }
        except Exception as e:
            logger.error(f"Error getting flow statistics: {e}")
            return {
                "error": str(e),
                "flow_statistics": {
                    "total_flows": 0,
                    "active_flows": 0,
                    "flows_per_switch": {},
                    "priority_distribution": {},
                    "table_distribution": {}
                },
                "utilization_metrics": {
                    "efficiency_percentage": 0,
                    "efficiency_rating": "poor"
                }
            }