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
Smart City policy implementation for federated learning.
Focuses on IoT device efficiency and geographic distribution.
"""

from typing import Dict, List, Any, Optional
import logging

from src.core.policies.policy import Policy

logger = logging.getLogger(__name__)


class SmartCityPolicy(Policy):
    """
    Policy for smart city applications in federated learning.
    Focuses on bandwidth efficiency, geographic distribution, and IoT device constraints.
    """

    def __init__(
        self,
        policy_id: str,
        name: str = "Smart City Policy",
        description: str = "Traffic prediction policy for IoT devices",
        rules: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a smart city policy.

        Args:
            policy_id: Unique identifier for the policy
            name: Human-readable name for the policy
            description: Description of the policy's purpose
            rules: Policy rules
            metadata: Additional metadata
        """
        if rules is None:
            rules = self._get_default_smart_city_rules()
        
        if metadata is None:
            metadata = {}
        
        # Add smart city-specific metadata
        metadata["domain"] = "smart_city"
        metadata["application"] = "traffic_prediction"
        metadata["target_devices"] = "iot"
        
        super().__init__(policy_id, name, description, rules, metadata)
    
    def _get_default_smart_city_rules(self) -> Dict[str, Any]:
        """
        Get default rules for smart city applications.
        
        Returns:
            Default smart city policy rules
        """
        return {
            "bandwidth_optimization": {
                "enabled": True,
                "max_upload_size_kb": 500,
                "compression_enabled": True,
                "compression_ratio": 0.2
            },
            "geographic_distribution": {
                "enabled": True,
                "min_geographic_regions": 3,
                "max_clients_per_region": 10,
                "region_diversity_required": True
            },
            "device_requirements": {
                "min_battery_percent": 30,
                "min_memory_mb": 50,
                "min_network_speed_mbps": 1.0,
                "supported_device_types": ["traffic_sensor", "camera", "environmental_sensor", "signal_controller"]
            },
            "data_freshness": {
                "max_data_age_minutes": 30,
                "real_time_priority": True
            },
            "aggregation": {
                "method": "weighted_average",
                "weights_by_data_quality": True,
                "min_clients": 10
            },
            "scheduling": {
                "off_peak_preferred": True,
                "max_training_duration_minutes": 5,
                "frequency": "hourly"
            }
        }
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy against the given context.
        
        Args:
            context: Contextual information for policy evaluation
            
        Returns:
            Evaluation result with recommendations
        """
        result = {
            "compliant": True,
            "recommendations": [],
            "violations": [],
            "applied_rules": []
        }
        
        # Check for device requirements
        if "device" in context and "device_requirements" in self.rules:
            self._evaluate_device_requirements(context, result)
        
        # Check for bandwidth optimization
        if "network" in context and "bandwidth_optimization" in self.rules:
            self._evaluate_bandwidth_optimization(context, result)
        
        # Check for geographic distribution
        if "geographic_distribution" in self.rules and "regions" in context:
            self._evaluate_geographic_distribution(context, result)
        
        # Check for data freshness
        if "data_freshness" in self.rules and "data" in context:
            self._evaluate_data_freshness(context, result)
        
        return result
    
    def _evaluate_device_requirements(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Evaluate device requirements.
        
        Args:
            context: Contextual information for policy evaluation
            result: Evaluation result to update
        """
        device_rules = self.rules["device_requirements"]
        device = context.get("device", {})
        
        # Check battery level
        if "battery_percent" in device and device["battery_percent"] < device_rules["min_battery_percent"]:
            result["compliant"] = False
            result["violations"].append(
                f"Insufficient battery: {device['battery_percent']}% < {device_rules['min_battery_percent']}%"
            )
        
        # Check memory
        if "memory_mb" in device and device["memory_mb"] < device_rules["min_memory_mb"]:
            result["compliant"] = False
            result["violations"].append(
                f"Insufficient memory: {device['memory_mb']}MB < {device_rules['min_memory_mb']}MB"
            )
        
        # Check network speed
        if "network_speed_mbps" in device and device["network_speed_mbps"] < device_rules["min_network_speed_mbps"]:
            result["compliant"] = False
            result["violations"].append(
                f"Insufficient network speed: {device['network_speed_mbps']}Mbps < {device_rules['min_network_speed_mbps']}Mbps"
            )
        
        # Check device type
        if "type" in device and device["type"] not in device_rules["supported_device_types"]:
            result["compliant"] = False
            result["violations"].append(
                f"Unsupported device type: {device['type']}"
            )
    
    def _evaluate_bandwidth_optimization(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Evaluate bandwidth optimization rules.
        
        Args:
            context: Contextual information for policy evaluation
            result: Evaluation result to update
        """
        bandwidth_rules = self.rules["bandwidth_optimization"]
        network = context.get("network", {})
        
        if bandwidth_rules["enabled"]:
            result["applied_rules"].append("bandwidth_optimization")
            
            # Check if compression is enabled and recommended
            if bandwidth_rules["compression_enabled"] and not network.get("compression_enabled", False):
                result["recommendations"].append(
                    f"Enable compression with ratio {bandwidth_rules['compression_ratio']}"
                )
            
            # Check upload size
            if "upload_size_kb" in network and network["upload_size_kb"] > bandwidth_rules["max_upload_size_kb"]:
                result["compliant"] = False
                result["violations"].append(
                    f"Upload size too large: {network['upload_size_kb']}KB > {bandwidth_rules['max_upload_size_kb']}KB"
                )
    
    def _evaluate_geographic_distribution(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Evaluate geographic distribution rules.
        
        Args:
            context: Contextual information for policy evaluation
            result: Evaluation result to update
        """
        geo_rules = self.rules["geographic_distribution"]
        regions = context.get("regions", {})
        
        if geo_rules["enabled"]:
            result["applied_rules"].append("geographic_distribution")
            
            # Check number of regions
            region_count = len(regions.keys())
            if region_count < geo_rules["min_geographic_regions"]:
                result["compliant"] = False
                result["violations"].append(
                    f"Insufficient geographic diversity: {region_count} regions < {geo_rules['min_geographic_regions']}"
                )
            
            # Check clients per region
            for region, clients in regions.items():
                if len(clients) > geo_rules["max_clients_per_region"]:
                    result["compliant"] = False
                    result["violations"].append(
                        f"Too many clients in region {region}: {len(clients)} > {geo_rules['max_clients_per_region']}"
                    )
    
    def _evaluate_data_freshness(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Evaluate data freshness rules.
        
        Args:
            context: Contextual information for policy evaluation
            result: Evaluation result to update
        """
        freshness_rules = self.rules["data_freshness"]
        data = context.get("data", {})
        
        if "age_minutes" in data and data["age_minutes"] > freshness_rules["max_data_age_minutes"]:
            result["compliant"] = False
            result["violations"].append(
                f"Data too old: {data['age_minutes']} minutes > {freshness_rules['max_data_age_minutes']} minutes"
            )
            
            # Add recommendation for fresher data
            result["recommendations"].append(
                "Collect newer data before training"
            ) 