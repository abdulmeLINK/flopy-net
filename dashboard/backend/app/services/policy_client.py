"""
Direct HTTP client for the Policy Engine API.
This provides a clean async interface for the dashboard to interact with policy engine.
"""
from typing import Dict, Any, Optional, List
import asyncio
import logging
import httpx
from datetime import datetime
from fastapi import HTTPException

from ..core.config import settings

logger = logging.getLogger(__name__)

class AsyncPolicyEngineClient:
    """Direct HTTP client for the Policy Engine API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 10):
        """
        Initialize the Policy Engine API client.
        
        Args:
            base_url: URL of the Policy Engine API server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.POLICY_ENGINE_URL.rstrip('/')
        self.timeout = httpx.Timeout(
            connect=10.0,   # Increased connection timeout for policy updates
            read=timeout,   # Read timeout
            write=10.0,     # Increased write timeout for policy updates
            pool=timeout    # Pool timeout
        )
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True
        )
        
        logger.info(f"Initialized Policy Engine HTTP client connected to {self.base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info("Closed Policy Engine HTTP client.")
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Policy Engine API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON data for POST/PUT requests
            
        Returns:
            API response as a dict
        """
        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {method} {endpoint}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {method} {endpoint}: {e}")
            raise
    
    async def get_health(self) -> Dict[str, Any]:
        """Check the health of the Policy Engine."""
        try:
            return await self._make_request("GET", "/health")
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the status of the Policy Engine (alias for get_health)."""
        return await self.get_health()
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get the current connection status to the policy engine."""
        try:
            health = await self.get_health()
            connected = "error" not in health
            
            return {
                "connected": connected,
                "url": self.base_url,
                "status": "healthy" if connected else "disconnected",
                "last_check": datetime.now().isoformat(),
                "health_data": health
            }
        except Exception as e:
            logger.error(f"Error checking policy engine connection status: {e}")
            return {
                "connected": False,
                "url": self.base_url,
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def get_policies(self) -> List[Dict[str, Any]]:
        """Get all available policies from the policy engine."""
        try:
            # Try the v1 API first
            try:
                data = await self._make_request("GET", "/api/v1/policies")
                if isinstance(data, list):
                    policies = data
                elif isinstance(data, dict) and "policies" in data:
                    policies = data["policies"]
                else:
                    logger.warning(f"Unexpected policies response format: {type(data)}")
                    policies = []
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try legacy API
                    logger.info("v1 API not found, trying legacy API")
                    data = await self._make_request("GET", "/api/policies")
                    if isinstance(data, list):
                        policies = data
                    elif isinstance(data, dict) and "policies" in data:
                        policies = data["policies"]
                    else:
                        policies = []
                else:
                    raise

            # Transform policies to flatten the data structure
            flattened_policies = []
            for policy in policies:
                # The policy engine stores user data in a 'data' field
                policy_data = policy.get("data", {})
                
                # Create flattened policy structure
                flattened_policy = {
                    # Top-level metadata from policy engine
                    "id": policy.get("id"),
                    "type": policy.get("type"),
                    "created_at": policy.get("created_at"),
                    "updated_at": policy.get("updated_at"),
                    "enabled": policy.get("enabled", True),
                    "version": policy.get("version", 0),
                    
                    # User-provided data from the 'data' field
                    "name": policy_data.get("name", policy.get("name", "Unnamed Policy")),
                    "description": policy_data.get("description", policy.get("description", "")),
                    "priority": policy_data.get("priority", policy.get("priority", 100)),
                    "rules": policy_data.get("rules", policy.get("rules", [])),
                    
                    # Ensure status field
                    "status": "active" if policy.get("enabled", True) else "inactive",
                    
                    # Keep the original data for reference
                    "_original_data": policy_data
                }
                
                flattened_policies.append(flattened_policy)

            # Ensure policies have required fields with fallbacks
            for policy in flattened_policies:
                if "created_at" not in policy or not policy["created_at"]:
                    policy["created_at"] = datetime.now().isoformat()
                if "updated_at" not in policy or not policy["updated_at"]:
                    policy["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"Retrieved {len(flattened_policies)} policies from policy engine")
            return flattened_policies
            
        except Exception as e:
            logger.error(f"Failed to fetch policies from policy engine: {e}")
            # NO FALLBACKS - let the error surface so we can debug properly
            raise
    
    async def get_policy(self, policy_id: str) -> Dict[str, Any]:
        """Get a specific policy by ID."""
        try:
            return await self._make_request("GET", f"/api/v1/policies/{policy_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    return await self._make_request("GET", f"/api/policies/{policy_id}")
                except httpx.HTTPStatusError as e2:
                    if e2.response.status_code == 404:
                        raise HTTPException(status_code=404, detail="Policy not found")
                    raise
            raise
    
    async def get_policy_decisions(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get policy decisions from the policy engine."""
        try:
            # Try the v1 API first
            try:
                data = await self._make_request("GET", "/api/v1/policy_decisions", params=params)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Try legacy API
                    data = await self._make_request("GET", "/api/policy_decisions", params=params)
                else:
                    raise
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "decisions" in data:
                return data["decisions"]
            else:
                logger.warning(f"Unexpected policy decisions response format: {type(data)}")
                # NO FALLBACKS - throw error if unexpected format
                raise ValueError(f"Unexpected response format: {type(data)}")
                
        except Exception as e:
            logger.error(f"Failed to fetch policy decisions: {e}")
            # NO FALLBACKS - let the error surface so we can debug properly
            raise
    
    async def get_average_decision_time(self) -> float:
        """Get average decision time from recent policy decisions."""
        try:
            # Try to get metrics from the policy engine
            try:
                data = await self._make_request("GET", "/api/v1/metrics")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    data = await self._make_request("GET", "/metrics")
                else:
                    raise
            
            # Extract average decision time from metrics
            if isinstance(data, dict):
                avg_time = data.get("average_decision_time_ms", 0.0)
                if isinstance(avg_time, (int, float)):
                    return float(avg_time)
            
            # NO FALLBACKS - throw error if no valid data
            raise ValueError("No valid average decision time found in metrics")
            
        except Exception as e:
            logger.error(f"Failed to get average decision time: {e}")
            # NO FALLBACKS - let the error surface so we can debug properly
            raise
    
    async def create_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new policy."""
        try:
            return await self._make_request("POST", "/api/v1/policies", json_data=policy_data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self._make_request("POST", "/api/policies", json_data=policy_data)
            raise
    
    async def update_policy(self, policy_id: str, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing policy."""
        try:
            return await self._make_request("PUT", f"/api/v1/policies/{policy_id}", json_data=policy_data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self._make_request("PUT", f"/api/policies/{policy_id}", json_data=policy_data)
            raise
    
    async def delete_policy(self, policy_id: str) -> Dict[str, Any]:
        """Delete a policy."""
        try:
            return await self._make_request("DELETE", f"/api/v1/policies/{policy_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self._make_request("DELETE", f"/api/policies/{policy_id}")
            raise
    
    async def enable_policy(self, policy_id: str) -> Dict[str, Any]:
        """Enable a policy."""
        try:
            return await self._make_request("POST", f"/api/v1/policies/{policy_id}/enable")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self._make_request("POST", f"/api/policies/{policy_id}/enable")
            raise
    
    async def disable_policy(self, policy_id: str) -> Dict[str, Any]:
        """Disable a policy."""
        try:
            return await self._make_request("POST", f"/api/v1/policies/{policy_id}/disable")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self._make_request("POST", f"/api/policies/{policy_id}/disable")
            raise
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get policy engine metrics."""
        connection_status = await self.get_connection_status()
        policies = await self.get_policies()
        avg_decision_time = await self.get_average_decision_time()
        
        return {
            "total_policies": len(policies),
            "active_policies": len([p for p in policies if p.get("status") == "active"]),
            "average_decision_time_ms": avg_decision_time,
            "status": "healthy" if connection_status["connected"] else "disconnected",
            "connection_status": connection_status
        }
    
    async def get_policy_decision_details(self, decision_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific policy decision."""
        try:
            return await self._make_request("GET", f"/api/v1/policy_decisions/{decision_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                try:
                    return await self._make_request("GET", f"/api/policy_decisions/{decision_id}")
                except httpx.HTTPStatusError as e2:
                    if e2.response.status_code == 404:
                        raise HTTPException(status_code=404, detail="Policy decision not found")
                    raise
            raise
    
    async def get_rule_performance_analytics(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get analytics on rule performance and effectiveness."""
        try:
            return await self._make_request("GET", "/api/v1/analytics/rule_performance", params=params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # NO FALLBACKS - throw error if endpoint doesn't exist
                raise ValueError("Rule performance analytics endpoint not available")
            raise
        except Exception as e:
            logger.error(f"Failed to get rule performance analytics: {e}")
            # NO FALLBACKS - let the error surface so we can debug properly
            raise
    
    async def get_decision_pattern_analytics(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get analytics on decision patterns and trends."""
        try:
            return await self._make_request("GET", "/api/v1/analytics/decision_patterns", params=params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # NO FALLBACKS - throw error if endpoint doesn't exist
                raise ValueError("Decision pattern analytics endpoint not available")
            raise
        except Exception as e:
            logger.error(f"Failed to get decision pattern analytics: {e}")
            # NO FALLBACKS - let the error surface so we can debug properly
            raise
    
    async def get_policy_metrics_timeseries(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get policy metrics time series data."""
        try:
            data = await self._make_request("GET", "/api/v1/policy_metrics", params=params)
            
            if isinstance(data, dict) and "metrics" in data:
                return data["metrics"]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected policy metrics response format: {type(data)}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch policy metrics time series: {e}")
            raise
    
    async def get_policy_version(self) -> Dict[str, Any]:
        """Get current policy version for cache validation."""
        try:
            return await self._make_request("GET", "/api/v1/policy_version")
        except Exception as e:
            logger.error(f"Failed to get policy version: {e}")
            raise
    
    async def check_policy_cache_validity(self, client_version: int) -> Dict[str, Any]:
        """Check if client's cached policy version is still valid."""
        try:
            return await self._make_request(
                "POST", 
                "/api/v1/policy_cache_check",
                json_data={"policy_version": client_version}
            )
        except Exception as e:
            logger.error(f"Failed to check policy cache validity: {e}")
            raise
    
    async def notify_policy_update(self, policy_id: str) -> Dict[str, Any]:
        """Notify policy engine about policy update to trigger refresh in components."""
        try:
            return await self._make_request(
                "POST", 
                "/api/v1/notify_policy_update",
                json_data={"policy_id": policy_id}
            )
        except Exception as e:
            logger.error(f"Failed to notify policy update for {policy_id}: {e}")
            raise
    
    async def get_policy_history(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get policy modification history with optional filtering."""
        try:
            return await self._make_request("GET", "/api/v1/policy_history", params=params)
        except Exception as e:
            logger.error(f"Failed to fetch policy history: {e}")
            raise