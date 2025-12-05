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
Application Tracker Module.

This module provides classes for tracking policy applications and statistics.
"""

import logging
import time
import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ApplicationTracker:
    """Tracks policy applications for history and statistics."""
    
    def __init__(self, max_application_history: int = 1000, cleanup_interval: int = 3600):
        """
        Initialize the application tracker.
        
        Args:
            max_application_history: Maximum number of applications to keep in history
            cleanup_interval: Interval in seconds between memory cleanups
        """
        self.policy_applications: List[Dict[str, Any]] = []
        self.policy_application_stats = {
            "total_checks": 0,
            "allowed_checks": 0,
            "denied_checks": 0,
            "by_component": {},
            "by_policy_type": {},
            "by_requester": {}
        }
        self.max_application_history = max_application_history
        self._last_cleanup_time = time.time()
        self._cleanup_interval = cleanup_interval
    
    def record_policy_application(self, policy_type: str, requester_id: str, component: str, 
                                   action: str, context: Dict[str, Any], result: bool,
                                   reason: str, policies_checked: List[str], policy_count: int,
                                   evaluation_time_ms: float, violations: List[Dict[str, Any]]) -> None:
        """Record a policy application for history tracking and statistics."""
        timestamp = time.time()
        
        # Create application record with filtered context (exclude sensitive data)
        application_record = {
            "timestamp": timestamp,
            "iso_time": datetime.datetime.now().isoformat(),
            "policy_type": policy_type,
            "requester_id": requester_id,
            "component": component,
            "action": action,
            "context": {k: v for k, v in context.items() if k not in ['password', 'token', 'secret', 'sensitive_data']},
            "result": result,
            "reason": reason,
            "policies_checked": policies_checked,
            "policy_count": policy_count,
            "evaluation_time_ms": evaluation_time_ms,
            "violations": violations if violations else []
        }
        
        # Update statistics
        self.policy_application_stats["total_checks"] += 1
        if result:
            self.policy_application_stats["allowed_checks"] += 1
        else:
            self.policy_application_stats["denied_checks"] += 1
        
        # Update component stats
        if component not in self.policy_application_stats["by_component"]:
            self.policy_application_stats["by_component"][component] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_component"][component]["total"] += 1
        if result:
            self.policy_application_stats["by_component"][component]["allowed"] += 1
        else:
            self.policy_application_stats["by_component"][component]["denied"] += 1
        
        # Update policy type stats
        if policy_type not in self.policy_application_stats["by_policy_type"]:
            self.policy_application_stats["by_policy_type"][policy_type] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_policy_type"][policy_type]["total"] += 1
        if result:
            self.policy_application_stats["by_policy_type"][policy_type]["allowed"] += 1
        else:
            self.policy_application_stats["by_policy_type"][policy_type]["denied"] += 1
        
        # Update requester stats
        if requester_id not in self.policy_application_stats["by_requester"]:
            self.policy_application_stats["by_requester"][requester_id] = {"total": 0, "allowed": 0, "denied": 0}
        self.policy_application_stats["by_requester"][requester_id]["total"] += 1
        if result:
            self.policy_application_stats["by_requester"][requester_id]["allowed"] += 1
        else:
            self.policy_application_stats["by_requester"][requester_id]["denied"] += 1
        
        # Add to history with size limit
        self.policy_applications.append(application_record)
        if len(self.policy_applications) > self.max_application_history:
            self.policy_applications = self.policy_applications[-self.max_application_history:]
        
        # Periodic memory cleanup (every 100 applications)
        if len(self.policy_applications) % 100 == 0:
            self.cleanup_memory()
        
        logger.debug(f"Recorded policy application: {policy_type} for {component} by {requester_id}")
    
    def get_policy_applications(self, policy_type=None, component=None, requester_id=None, 
                               result=None, limit=100, start_time=None, end_time=None) -> List[Dict[str, Any]]:
        """
        Get history of policy applications with filtering options.
        
        Args:
            policy_type: Filter by policy type
            component: Filter by component name
            requester_id: Filter by requester ID
            result: Filter by result (True/False)
            limit: Maximum number of results to return
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            
        Returns:
            List of policy applications
        """
        # Get applications history
        applications = self.policy_applications
        
        # Apply filters
        if policy_type:
            applications = [a for a in applications if a.get('policy_type') == policy_type]
        if component:
            applications = [a for a in applications if a.get('component') == component]
        if requester_id:
            applications = [a for a in applications if a.get('requester_id') == requester_id]
        if result is not None:
            applications = [a for a in applications if a.get('result') == result]
        if start_time:
            try:
                start_timestamp = float(start_time)
                applications = [a for a in applications if a.get('timestamp') >= start_timestamp]
            except (ValueError, TypeError):
                pass
        if end_time:
            try:
                end_timestamp = float(end_time)
                applications = [a for a in applications if a.get('timestamp') <= end_timestamp]
            except (ValueError, TypeError):
                pass
        
        # Sort by timestamp (newest first) and limit results
        applications = sorted(applications, key=lambda x: x.get('timestamp', 0), reverse=True)[:limit]
        
        return applications
    
    def cleanup_memory(self, max_policy_history: int = 500) -> None:
        """Clean up memory by removing old data."""
        current_time = time.time()
        
        # Only cleanup if enough time has passed
        if current_time - self._last_cleanup_time < self._cleanup_interval:
            return
        
        try:
            # Cleanup policy applications
            if len(self.policy_applications) > self.max_application_history:
                # Keep only recent applications
                keep_count = int(self.max_application_history * 0.8)  # Keep 80%
                self.policy_applications = self.policy_applications[-keep_count:]
                logger.info(f"Cleaned up policy applications, keeping {keep_count} recent entries")
            
            # Cleanup component stats (keep only top 50 components)
            if len(self.policy_application_stats["by_component"]) > 50:
                # Sort by usage and keep top components
                sorted_components = sorted(
                    self.policy_application_stats["by_component"].items(),
                    key=lambda x: x[1].get("total", 0),
                    reverse=True
                )[:50]
                self.policy_application_stats["by_component"] = dict(sorted_components)
            
            # Similar cleanup for requesters
            if len(self.policy_application_stats["by_requester"]) > 100:
                sorted_requesters = sorted(
                    self.policy_application_stats["by_requester"].items(),
                    key=lambda x: x[1].get("total", 0),
                    reverse=True
                )[:100]
                self.policy_application_stats["by_requester"] = dict(sorted_requesters)
            
            self._last_cleanup_time = current_time
            logger.debug("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get policy application statistics."""
        return self.policy_application_stats.copy()
