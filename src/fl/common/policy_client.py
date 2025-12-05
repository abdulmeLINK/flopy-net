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
Policy Client for FL Components

This module provides a shared policy client for checking policies with the
policy engine. Used by both FL server and FL client to avoid code duplication.
"""

import json
import hashlib
import time
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PolicyEnforcementError(Exception):
    """Exception raised when policy enforcement fails."""
    pass


class PolicyClient:
    """
    Client for interacting with the policy engine.
    
    This class provides methods for checking policies, verifying results,
    and managing policy signatures to prevent replay attacks.
    """
    
    def __init__(
        self,
        policy_engine_url: str = "http://localhost:5000",
        auth_token: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: int = 2,
        strict_mode: bool = True,
        cache_ttl: int = 10
    ):
        """
        Initialize the policy client.
        
        Args:
            policy_engine_url: URL of the policy engine
            auth_token: Optional authentication token
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Seconds to wait between retries
            strict_mode: If True, raise exceptions on policy check failures
            cache_ttl: Cache TTL for policy signatures in seconds
        """
        self.policy_engine_url = policy_engine_url
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.strict_mode = strict_mode
        self.cache_ttl = cache_ttl
        
        # Policy version tracking
        self.cached_policy_version = 0
        self.last_policy_version_check = 0
        self.policy_version_check_interval = 30  # seconds
        
        # Signature tracking for verification
        self.policy_check_signatures: Dict[str, Dict[str, Any]] = {}
        self.last_policy_check_time: Optional[float] = None
        
        # Metrics tracking
        self.checks_performed = 0
        self.checks_allowed = 0
        self.checks_denied = 0
    
    def create_signature(self, policy_type: str, context: Dict[str, Any]) -> str:
        """
        Create a unique signature for the policy check to prevent replay attacks.
        
        Args:
            policy_type: Type of policy check
            context: Context for policy check
            
        Returns:
            Unique signature string
        """
        context_str = json.dumps(context, sort_keys=True)
        data = f"{policy_type}:{context_str}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def check_version_and_refresh(self) -> bool:
        """
        Check if policy version has changed and refresh if needed.
        
        Returns:
            True if policies were refreshed, False otherwise
        """
        current_time = time.time()
        
        # Only check version periodically
        if current_time - self.last_policy_version_check < self.policy_version_check_interval:
            return False
        
        try:
            version_url = f"{self.policy_engine_url}/api/v1/policy_version"
            response = requests.get(version_url, timeout=self.timeout)
            
            if response.status_code == 200:
                version_data = response.json()
                current_version = version_data.get("policy_version", 0)
                
                self.last_policy_version_check = current_time
                
                if current_version > self.cached_policy_version:
                    logger.info(f"Policy version changed from {self.cached_policy_version} to {current_version}")
                    self.cached_policy_version = current_version
                    self.policy_check_signatures.clear()
                    return True
                    
        except Exception as e:
            logger.warning(f"Failed to check policy version: {e}")
            
        return False
    
    def check_policy(
        self,
        policy_type: str,
        context: Dict[str, Any],
        extra_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if an action is allowed by the policy engine.
        
        Args:
            policy_type: Type of policy to check
            context: Context information for policy evaluation
            extra_context: Additional context to merge (optional)
            
        Returns:
            Dictionary with policy decision and metadata
        """
        # Check for policy version updates
        self.check_version_and_refresh()
        
        self.checks_performed += 1
        
        try:
            # Merge extra context if provided
            if extra_context:
                context = {**context, **extra_context}
            
            # Add timestamp to prevent replay attacks
            context["timestamp"] = time.time()
            
            # Create and store signature
            signature = self.create_signature(policy_type, context)
            context["signature"] = signature
            
            self.policy_check_signatures[signature] = {
                "policy_type": policy_type,
                "timestamp": context["timestamp"]
            }
            self.last_policy_check_time = time.time()
            
            # Prepare request
            headers = {'Content-Type': 'application/json'}
            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"
            
            payload = {
                'policy_type': policy_type,
                'context': context
            }
            
            # Try with retries
            result = self._try_policy_request(headers, payload, signature)
            
            # Track metrics
            if result.get('allowed'):
                self.checks_allowed += 1
            else:
                self.checks_denied += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking policy: {e}")
            self.checks_denied += 1
            
            if self.strict_mode:
                raise PolicyEnforcementError(f"Policy check error: {str(e)}")
            
            return {
                "allowed": True,
                "reason": f"Error checking policy: {e}",
                "signature": "error"
            }
    
    def _try_policy_request(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """
        Try to make a policy request with retries and fallback.
        
        Args:
            headers: Request headers
            payload: Request payload
            signature: Policy signature
            
        Returns:
            Policy result dictionary
        """
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            if retries > 0:
                logger.warning(f"Retrying policy check ({retries}/{self.max_retries})")
                time.sleep(self.retry_delay)
            
            # Try v1 API first
            result = self._try_v1_api(headers, payload, signature)
            if result is not None:
                return result
            
            # Try legacy API
            result = self._try_legacy_api(headers, payload, signature)
            if result is not None:
                return result
            
            retries += 1
        
        # All retries failed
        error_msg = f"Policy check failed after {retries} retries"
        logger.error(error_msg)
        
        if self.strict_mode:
            raise PolicyEnforcementError(error_msg)
        
        return {
            "allowed": True,
            "reason": f"Policy engine unavailable after {retries} retries",
            "signature": signature
        }
    
    def _try_v1_api(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """Try the v1 API endpoint."""
        try:
            response = requests.post(
                f"{self.policy_engine_url}/api/v1/check",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            result["signature"] = signature
            logger.info(f"Policy check result from v1 API: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"v1 API failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in v1 API: {e}")
            return None
    
    def _try_legacy_api(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """Try the legacy API endpoint."""
        try:
            response = requests.post(
                f"{self.policy_engine_url}/api/check_policy",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            result["signature"] = signature
            logger.info(f"Policy check result from legacy API: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Legacy API failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error in legacy API: {e}")
            return None
    
    def verify_result(self, result: Dict[str, Any], max_age: int = 60) -> bool:
        """
        Verify that a policy result is valid and hasn't been tampered with.
        
        Args:
            result: Policy check result including signature
            max_age: Maximum age of the check in seconds
            
        Returns:
            True if valid, False otherwise
        """
        if "signature" not in result:
            logger.error("Policy result missing signature")
            return False
        
        signature = result["signature"]
        
        if signature == "error":
            logger.warning("Policy result has error signature")
            return False
        
        if signature not in self.policy_check_signatures:
            logger.error(f"Unknown policy signature: {signature}")
            return False
        
        check_info = self.policy_check_signatures[signature]
        
        if time.time() - check_info["timestamp"] > max_age:
            logger.error(f"Policy check expired: {signature}")
            return False
        
        return True
    
    def get_metrics(self) -> Dict[str, int]:
        """Get policy check metrics."""
        return {
            "checks_performed": self.checks_performed,
            "checks_allowed": self.checks_allowed,
            "checks_denied": self.checks_denied
        }
    
    def clear_signature_cache(self) -> None:
        """Clear the signature cache."""
        self.policy_check_signatures.clear()
