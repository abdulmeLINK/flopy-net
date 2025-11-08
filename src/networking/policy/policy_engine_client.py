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
Policy Engine Client for SDN Integration.

This module provides a client for the remote policy engine service,
implementing the same interface as the local PolicyEngine class.
"""

import time
import threading
import requests
import json
from typing import Dict, List, Optional, Any, Union, Callable

from src.core.common.logger import LoggerMixin
from src.networking.policy.network_policy_handler import IPolicyEngine

class PolicyEngineClient(IPolicyEngine):
    """Client for the remote policy engine service."""
    
    def __init__(self, policy_engine_url: str = "http://policy-engine:5000", 
                 refresh_interval: int = 15, northbound_interface: Optional[str] = None):
        """
        Initialize the policy engine client.
        
        Args:
            policy_engine_url: URL of the policy engine service
            refresh_interval: Interval to refresh policies in seconds
            northbound_interface: Network interface to use for policy engine communication
        """
        super().__init__()
        self.policy_engine_url = policy_engine_url
        self.refresh_interval = refresh_interval
        self.northbound_interface = northbound_interface
        self.policies = []  # Cached policies
        self.callbacks = []  # List of registered callbacks
        self.stop_refresh = False
        self.refresh_thread = None
        self._last_fetch_successful: bool = False
        self._lock = threading.Lock() # Lock for accessing shared state
        
        # Start refresh thread
        self.refresh_thread = threading.Thread(target=self._refresh_policies)
        self.refresh_thread.daemon = True
        self.refresh_thread.start()
        
        self.logger.info(f"Initialized policy engine client connected to {policy_engine_url}")
    
    def _refresh_policies(self) -> None:
        """Periodically refresh policies from the policy engine."""
        while not self.stop_refresh:
            try:
                old_policies = self.policies.copy()
                self.policies = self._fetch_policies()
                
                # Check if policies have changed
                if old_policies != self.policies:
                    self._notify_policy_change()
            except Exception as e:
                self.logger.error(f"Error refreshing policies: {e}")
            
            time.sleep(self.refresh_interval)
    
    def _fetch_policies(self) -> List[Dict[str, Any]]:
        """
        Fetch policies from the remote policy engine.
        Updates the internal status flag based on success.
        
        Returns:
            List[Dict[str, Any]]: List of policies, or empty list on failure.
        """
        current_fetch_successful = False
        try:
            # Try to fetch policies from the v1 API
            response = None
            api_url = f"{self.policy_engine_url}/api/v1/policies"
            legacy_api_url = f"{self.policy_engine_url}/api/policies"
            
            # Try v1 API first
            try:
                response = requests.get(api_url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    valid_policies = self._parse_and_normalize_policies(data)
                    self.logger.info(f"Fetched {len(valid_policies)} policies from v1 API ({api_url})")
                    current_fetch_successful = True
                    # Update status *after* successful fetch and parse
                    with self._lock:
                        self._last_fetch_successful = True
                    return valid_policies
                else:
                     self.logger.warning(f"Failed to fetch policies from v1 API ({api_url}): {response.status_code}, trying legacy.")

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Error connecting to v1 API ({api_url}): {e}, trying legacy.")
            
            # Fall back to legacy endpoint
            try:
                response = requests.get(legacy_api_url, timeout=5)
            
                if response.status_code == 200:
                    data = response.json()
                    valid_policies = self._parse_and_normalize_policies(data)
                    self.logger.info(f"Fetched {len(valid_policies)} policies from legacy API ({legacy_api_url})")
                    current_fetch_successful = True
                    # Update status *after* successful fetch and parse
                    with self._lock:
                        self._last_fetch_successful = True
                    return valid_policies
                else:
                    self.logger.error(f"Failed to fetch policies from legacy API ({legacy_api_url}): {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                 self.logger.error(f"Error connecting to legacy API ({legacy_api_url}): {e}")
                 
        except Exception as e:
            # Catch any other unexpected errors during fetching/parsing
            self.logger.error(f"Unexpected error fetching policies: {e}")

        # If we reached here, the fetch failed
        if not current_fetch_successful:
             with self._lock:
                self._last_fetch_successful = False
        return [] # Return empty list on any failure

    def _parse_and_normalize_policies(self, data: Union[List, Dict]) -> List[Dict[str, Any]]:
        """Parses raw policy data and normalizes it."""
        policies = []
        if isinstance(data, dict) and "policies" in data:
            policies = data["policies"]
        elif isinstance(data, list):
            policies = data
        else:
            self.logger.warning(f"Received unexpected policy data format: {type(data)}")
            return []
        
        valid_policies = []
        for idx, policy in enumerate(policies):
            if isinstance(policy, dict) and ("type" in policy or "policy_type" in policy):
                # Ensure ID exists
                if "id" not in policy:
                    policy["id"] = f"policy-{idx}" # Generate placeholder ID
                
                # Normalize policy type field
                if "type" in policy and "policy_type" not in policy:
                    policy["policy_type"] = policy["type"]
                elif "policy_type" in policy and "type" not in policy:
                    policy["type"] = policy["policy_type"]
                
                # Normalize network security type
                if policy.get("type") == "network":
                    policy["type"] = "network_security"
                    policy["policy_type"] = "network_security"
                
                valid_policies.append(policy)
            else:
                 self.logger.warning(f"Skipping invalid policy entry: {policy}")
        return valid_policies
        
    def check_policy_engine_status(self) -> bool:
        """Check if the last policy fetch attempt was successful."""
        with self._lock:
            return self._last_fetch_successful
    
    def _notify_policy_change(self) -> None:
        """Notify registered callbacks about policy changes."""
        for callback in self.callbacks:
            try:
                callback(self.policies)
            except Exception as e:
                self.logger.error(f"Error in policy callback: {e}")
    
    def validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a network policy against defined rules.
        
        Args:
            policy: Network policy configuration
            
        Returns:
            Dict: Validation result with status and message
        """
        try:
            # Format policy correctly for API
            policy_type = policy.get("type", "network_security")
            
            # Create properly structured payload with type and data fields
            api_payload = {
                "type": policy_type,
                "data": policy
            }
            
            # Try the v1 API endpoint first
            response = None
            try:
                response = requests.post(
                    f"{self.policy_engine_url}/api/v1/validate_policy",
                    json=api_payload,
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info(f"Successfully validated policy against v1 API")
                    return result
                else:
                    self.logger.warning(f"v1 API returned {response.status_code}, trying legacy endpoint")
            except Exception as e:
                self.logger.warning(f"Error validating policy with v1 API: {e}, trying legacy endpoint")
            
            # Fall back to legacy endpoint
            response = requests.post(
                f"{self.policy_engine_url}/api/validate_policy",
                json=policy,  # Legacy API might expect unwrapped format
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Successfully validated policy against legacy API")
                return result
            else:
                self.logger.error(f"Failed to validate policy: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"Policy engine returned status code {response.status_code}"
                }
                
        except Exception as e:
            self.logger.error(f"Error validating policy: {e}")
            return {
                "status": "error",
                "message": f"Error validating policy: {str(e)}"
            }
    
    def authorize_flow(self, src_ip: str, dst_ip: str, 
                     protocol: str = "any", port: int = 0) -> bool:
        """
        Check if a flow is authorized based on security policies.
        
        Args:
            src_ip: Source IP address
            dst_ip: Destination IP address
            protocol: Protocol (tcp, udp, icmp, any)
            port: Destination port
            
        Returns:
            bool: Whether the flow is authorized
        """
        try:
            payload = {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "protocol": protocol,
                "port": port
            }
            
            response = requests.post(
                f"{self.policy_engine_url}/api/authorize_flow",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("authorized", True)
            else:
                self.logger.error(f"Failed to authorize flow: {response.status_code}")
                # Default to allow if policy engine is unreachable
                return True
                
        except Exception as e:
            self.logger.error(f"Error authorizing flow: {e}")
            # Default to allow if policy engine is unreachable
            return True
    
    def get_client_priority(self, client_id: str) -> str:
        """
        Get the priority level for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            str: Priority level (high, medium, low)
        """
        try:
            response = requests.get(
                f"{self.policy_engine_url}/api/client_priority/{client_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("priority", "low")
            else:
                self.logger.error(f"Failed to get client priority: {response.status_code}")
                return "low"
                
        except Exception as e:
            self.logger.error(f"Error getting client priority: {e}")
            return "low"
    
    def register_policy_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for policy updates.
        
        Args:
            callback: Function to call when policies are updated
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self.logger.info("Registered policy callback")
    
    def unregister_policy_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Unregister a previously registered callback.
        
        Args:
            callback: Function to unregister
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            self.logger.info("Unregistered policy callback")
    
    def cleanup(self) -> None:
        """Clean up resources when shutting down."""
        self.stop_refresh = True
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1.0)
        self.callbacks = []
    
    def get_policies(self) -> List[Dict[str, Any]]:
        """
        Get all active policies.
        
        Returns:
            List[Dict[str, Any]]: List of active policies
        """
        return self.policies
    
    def apply_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a policy to the policy engine.
        
        Args:
            policy: Policy data to apply
            
        Returns:
            Dict: Result with status and ID if successful
        """
        try:
            # Format policy correctly for API
            policy_type = policy.get("type", "network_security")
            
            # Create properly structured payload with type and data fields
            api_payload = {
                "type": policy_type,
                "data": policy
            }
            
            # Try the v1 API endpoint
            response = requests.post(
                f"{self.policy_engine_url}/api/v1/policies",
                json=api_payload,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                policy_id = result.get("id")
                self.logger.info(f"Successfully applied policy, received ID: {policy_id}")
                
                # Trigger a refresh to get the latest policies
                try:
                    self.policies = self._fetch_policies()
                    self._notify_policy_change()
                except Exception as e:
                    self.logger.warning(f"Error refreshing policies after applying new policy: {e}")
                
                return {
                    "status": "success",
                    "id": policy_id,
                    "message": "Policy applied successfully"
                }
            else:
                error_msg = "Unknown error"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Unknown error")
                except:
                    error_msg = f"Status code: {response.status_code}"
                    
                self.logger.error(f"Failed to apply policy: {error_msg}")
                return {
                    "status": "error",
                    "message": f"Failed to apply policy: {error_msg}"
                }
                
        except Exception as e:
            self.logger.error(f"Error applying policy: {e}")
            return {
                "status": "error",
                "message": f"Error applying policy: {str(e)}"
            } 