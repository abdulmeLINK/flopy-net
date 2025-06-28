---
sidebar_position: 3
---

# Advanced Configuration and Customization

This tutorial covers advanced FLOPY-NET configuration techniques for sophisticated research scenarios, including custom federated learning implementations, complex network topologies, advanced policy management, and system optimization for research environments.

## Configuration Overview for Research Environments

FLOPY-NET's advanced configuration capabilities enable researchers to create sophisticated experimental environments that extend beyond the base simulation framework. While the current v1.0.0-alpha.8 implementation provides federated learning simulation with synthetic data, the configuration system is designed to support custom implementations that introduce real machine learning training, complex network scenarios, and advanced policy enforcement.

This tutorial demonstrates how to configure FLOPY-NET for various research scenarios including network behavior studies, policy enforcement research, system scalability analysis, and the foundation for implementing actual federated learning algorithms. The configuration approaches shown here provide the framework for transitioning from simulation to production-ready federated learning deployments.

## Custom Implementation Framework

### Building Real FL Algorithm Implementations

While the base FLOPY-NET images simulate federated learning behavior, researchers can implement actual federated learning algorithms by extending the base configuration and container framework. The following example demonstrates the configuration structure needed to support real FedProx implementation:

```python
# Example: Configuration for actual FedProx implementation
# This would replace the simulation logic in custom containers

class FedProxConfiguration:
    """
    Configuration template for implementing real FedProx algorithm
    within custom FLOPY-NET containers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Real training parameters (vs simulation parameters)
        self.algorithm_name = "FedProx"
        self.simulation_mode = config.get("simulation_mode", False)
        self.mu = config.get("mu", 0.1)  # Proximal term coefficient
        self.dataset_path = config.get("dataset_path", "/app/datasets")
        self.model_architecture = config.get("model_architecture", "resnet18")
        
        # Network-aware training parameters
        self.adaptive_mu = config.get("adaptive_mu", True)
        self.network_condition_adjustment = config.get("network_adjustment", True)
        self.policy_integration = config.get("policy_integration", True)
        
    def configure_for_simulation(self):
        """Configure for FLOPY-NET simulation mode (current default)"""
        return {
            "training_mode": "simulation",
            "data_source": "synthetic",
            "training_rounds": "mock",
            "metrics_generation": "artificial",
            "computation_requirements": "minimal"
        }
    
    def configure_for_real_training(self):
        """Configure for actual federated learning implementation"""
        return {
            "training_mode": "real",
            "data_source": self.dataset_path,
            "model_path": "/app/models",
            "training_rounds": "actual",
            "metrics_generation": "computed", 
            "computation_requirements": "full"
        }
```

### Container Configuration for Custom Implementations

Custom federated learning implementations require modified container configurations that support both simulation and real training modes:

```python
def get_client_update(self, local_model, train_loader):
    """Example client update method for real FL implementation."""
    return {
        "model_parameters": {name: param.data.clone() 
                           for name, param in local_model.named_parameters()},
        "num_samples": len(train_loader.dataset)
    }
```

```python
def adapt_mu(self, client_id: str, training_loss: float, proximal_loss: float) -> float:
        """
        Adaptively adjust the proximal term coefficient.
        """
        if self.mu_adaptation_strategy == "divergence_based":
            # Increase mu if model is diverging too much from global model
            divergence_ratio = proximal_loss / (training_loss + 1e-8)
            
            if divergence_ratio > 1.0:
                new_mu = min(self.mu * 1.1, 1.0)  # Increase mu, cap at 1.0
            elif divergence_ratio < 0.1:
                new_mu = max(self.mu * 0.9, 0.01)  # Decrease mu, floor at 0.01
            else:
                new_mu = self.mu
                
        elif self.mu_adaptation_strategy == "loss_based":
            # Adapt based on training loss progression
            if training_loss > self.previous_losses.get(client_id, float('inf')):
                new_mu = min(self.mu * 1.05, 1.0)
            else:
                new_mu = max(self.mu * 0.95, 0.01)
        else:
            new_mu = self.mu
            
        return new_mu
    
    def aggregate_models(self, client_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate model updates with weighted averaging.
        """
        total_samples = sum(update["num_samples"] for update in client_updates)
        
        # Initialize aggregated parameters
        aggregated_params = {}
        
        for update in client_updates:
            weight = update["num_samples"] / total_samples
            
            for param_name, param_value in update["model_parameters"].items():
                if param_name not in aggregated_params:
                    aggregated_params[param_name] = torch.zeros_like(param_value)
                
                aggregated_params[param_name] += weight * param_value
        
        # Calculate aggregation statistics
        avg_training_loss = sum(update["training_loss"] for update in client_updates) / len(client_updates)
        avg_proximal_loss = sum(update["proximal_loss"] for update in client_updates) / len(client_updates)
        
        return {
            "aggregated_parameters": aggregated_params,
            "participating_clients": len(client_updates),
            "total_samples": total_samples,
            "average_training_loss": avg_training_loss,
            "average_proximal_loss": avg_proximal_loss,
            "mu_values": {update["client_id"]: update["mu_used"] for update in client_updates}
        }
```

### Algorithm Configuration

```json
{
  "fl_algorithm": {
    "name": "FedProx",
    "class": "src.fl.algorithms.fedprox.FedProxAlgorithm",
    "parameters": {
      "mu": 0.1,
      "adaptive_mu": true,
      "mu_adaptation_strategy": "divergence_based",
      "mu_bounds": [0.01, 1.0],
      "adaptation_frequency": 1
    }
  },
  "training_config": {
    "local_epochs": 5,
    "learning_rate": 0.01,
    "batch_size": 32,
    "convergence_threshold": 0.001,
    "max_rounds": 50
  }
}
```

## Advanced Network Configuration

### Complex Network Topologies

Define sophisticated network architectures:

```python
# scenarios/network_topologies/hierarchical_edge.py
class HierarchicalEdgeTopology:
    """
    Multi-tier hierarchical topology with edge computing layers.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.topology = self.build_topology()
    
    def build_topology(self) -> Dict[str, Any]:
        """
        Build a hierarchical edge computing topology.
        
        Architecture:
        - Core Cloud (FL Server)
        - Regional Edge Nodes (Aggregation)
        - Local Edge Nodes (Client Clusters)
        - End Devices (FL Clients)
        """
        
        topology = {
            "topology_type": "hierarchical_edge",
            "layers": {
                "core": {
                    "nodes": [
                        {
                            "node_id": "cloud-core-1",
                            "type": "fl_server",
                            "resources": {
                                "cpu_cores": 32,
                                "memory_gb": 128,
                                "storage_gb": 2000,
                                "network_bandwidth_gbps": 10
                            },
                            "location": {"region": "us-east-1", "zone": "a"}
                        }
                    ]
                },
                "regional_edge": {
                    "nodes": [
                        {
                            "node_id": f"regional-edge-{i}",
                            "type": "edge_aggregator",
                            "resources": {
                                "cpu_cores": 16,
                                "memory_gb": 64,
                                "storage_gb": 500,
                                "network_bandwidth_gbps": 1
                            },
                            "location": {"region": f"region-{i}", "zone": "edge"},
                            "served_areas": [f"area-{i}-{j}" for j in range(3)]
                        }
                        for i in range(4)
                    ]
                },
                "local_edge": {
                    "nodes": [
                        {
                            "node_id": f"local-edge-{i}-{j}",
                            "type": "local_aggregator", 
                            "resources": {
                                "cpu_cores": 8,
                                "memory_gb": 32,
                                "storage_gb": 200,
                                "network_bandwidth_mbps": 500
                            },
                            "location": {"region": f"region-{i}", "area": f"area-{i}-{j}"},
                            "client_capacity": 10
                        }
                        for i in range(4) for j in range(3)
                    ]
                },
                "end_devices": {
                    "node_templates": [
                        {
                            "template_id": "high_end_device",
                            "count": 20,
                            "type": "fl_client",
                            "resources": {
                                "cpu_cores": 4,
                                "memory_gb": 8,
                                "storage_gb": 100,
                                "battery_capacity_wh": 50
                            },
                            "network_profile": "wifi_6"
                        },
                        {
                            "template_id": "mid_range_device",
                            "count": 40,
                            "type": "fl_client",
                            "resources": {
                                "cpu_cores": 2,
                                "memory_gb": 4,
                                "storage_gb": 50,
                                "battery_capacity_wh": 30
                            },
                            "network_profile": "wifi_5"
                        },
                        {
                            "template_id": "iot_device",
                            "count": 20,
                            "type": "fl_client",
                            "resources": {
                                "cpu_cores": 1,
                                "memory_gb": 1,
                                "storage_gb": 16,
                                "battery_capacity_wh": 10
                            },
                            "network_profile": "lte_cat_m"
                        }
                    ]
                }
            }
        }
        
        # Define connections between layers
        topology["connections"] = self.define_layer_connections()
        
        # Define network characteristics
        topology["network_profiles"] = self.define_network_profiles()
        
        return topology
    
    def define_layer_connections(self) -> List[Dict[str, Any]]:
        """Define connections between topology layers."""
        connections = []
        
        # Core to Regional Edge connections
        for i in range(4):
            connections.append({
                "from": "cloud-core-1",
                "to": f"regional-edge-{i}",
                "connection_type": "fiber_backbone",
                "characteristics": {
                    "bandwidth_gbps": 1,
                    "latency_ms": 10,
                    "reliability": 0.999,
                    "cost_per_gb": 0.001
                }
            })
        
        # Regional Edge to Local Edge connections
        for i in range(4):
            for j in range(3):
                connections.append({
                    "from": f"regional-edge-{i}",
                    "to": f"local-edge-{i}-{j}",
                    "connection_type": "metro_ethernet",
                    "characteristics": {
                        "bandwidth_mbps": 500,
                        "latency_ms": 5,
                        "reliability": 0.99,
                        "cost_per_gb": 0.01
                    }
                })
        
        return connections
    
    def define_network_profiles(self) -> Dict[str, Any]:
        """Define network profiles for different connection types."""
        return {
            "wifi_6": {
                "bandwidth_mbps": 100,
                "latency_ms": [5, 15],
                "reliability": 0.95,
                "power_consumption_w": 2
            },
            "wifi_5": {
                "bandwidth_mbps": 50,
                "latency_ms": [10, 25],
                "reliability": 0.90,
                "power_consumption_w": 3
            },
            "lte_cat_m": {
                "bandwidth_mbps": 1,
                "latency_ms": [50, 200],
                "reliability": 0.85,
                "power_consumption_w": 0.5
            }
        }
```

### Traffic Shaping and QoS

Implement advanced traffic management:

```python
# src/networking/traffic_manager.py
class AdvancedTrafficManager:
    """
    Advanced traffic management with QoS, traffic shaping, and 
    adaptive bandwidth allocation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.traffic_classes = self.define_traffic_classes()
        self.adaptive_policies = self.setup_adaptive_policies()
        
    def define_traffic_classes(self) -> Dict[str, Any]:
        """Define traffic classes with different QoS requirements."""
        return {
            "fl_control": {
                "priority": 1,  # Highest priority
                "bandwidth_allocation": "guaranteed",
                "min_bandwidth_mbps": 10,
                "max_latency_ms": 50,
                "jitter_tolerance_ms": 5,
                "packet_loss_tolerance": 0.001
            },
            "fl_model_updates": {
                "priority": 2,
                "bandwidth_allocation": "adaptive",
                "min_bandwidth_mbps": 50,
                "max_latency_ms": 200,
                "jitter_tolerance_ms": 20,
                "packet_loss_tolerance": 0.01,
                "compression_enabled": True
            },
            "fl_data_transfer": {
                "priority": 3,
                "bandwidth_allocation": "best_effort",
                "min_bandwidth_mbps": 1,
                "max_latency_ms": 1000,
                "jitter_tolerance_ms": 100,
                "packet_loss_tolerance": 0.05
            },
            "monitoring_metrics": {
                "priority": 4,
                "bandwidth_allocation": "background",
                "min_bandwidth_mbps": 0.1,
                "max_latency_ms": 5000,
                "compression_enabled": True,
                "aggregation_enabled": True
            }
        }
    
    def setup_adaptive_policies(self) -> List[Dict[str, Any]]:
        """Setup adaptive traffic management policies."""
        return [
            {
                "name": "congestion_control",
                "trigger": "network_utilization > 0.8",
                "actions": [
                    {
                        "type": "reduce_background_traffic",
                        "parameters": {"reduction_factor": 0.5}
                    },
                    {
                        "type": "enable_compression",
                        "parameters": {"traffic_classes": ["fl_model_updates", "monitoring_metrics"]}
                    },
                    {
                        "type": "increase_buffer_size",
                        "parameters": {"buffer_multiplier": 1.5}
                    }
                ]
            },
            {
                "name": "latency_optimization",
                "trigger": "average_latency > 100ms",
                "actions": [
                    {
                        "type": "prioritize_control_traffic",
                        "parameters": {"priority_boost": 1}
                    },
                    {
                        "type": "route_optimization",
                        "parameters": {"algorithm": "shortest_path"}
                    }
                ]
            },
            {
                "name": "client_adaptation",
                "trigger": "client_type == 'mobile' and battery_level < 0.3",
                "actions": [
                    {
                        "type": "reduce_transmission_power",
                        "parameters": {"power_reduction": 0.3}
                    },
                    {
                        "type": "increase_compression",
                        "parameters": {"compression_level": "high"}
                    }
                ]
            }
        ]
```

## Sophisticated Policy Management

### Multi-Layer Policy Architecture

Implement a hierarchical policy system:

```python
# src/policy_engine/advanced_policies.py
class MultiLayerPolicyEngine:
    """
    Advanced policy engine with multiple policy layers and 
    context-aware decision making.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.policy_layers = self.initialize_policy_layers()
        self.context_manager = ContextManager()
        self.policy_cache = PolicyCache()
        
    def initialize_policy_layers(self) -> Dict[str, Any]:
        """Initialize different policy layers."""
        return {
            "system_policies": SystemPolicyLayer(self.config.get("system_policies", {})),
            "experiment_policies": ExperimentPolicyLayer(self.config.get("experiment_policies", {})),
            "client_policies": ClientPolicyLayer(self.config.get("client_policies", {})),
            "network_policies": NetworkPolicyLayer(self.config.get("network_policies", {})),
            "security_policies": SecurityPolicyLayer(self.config.get("security_policies", {}))
        }
    
    def evaluate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a request against all policy layers with context awareness.
        """
        # Get current context
        context = self.context_manager.get_current_context()
        
        # Check policy cache first
        cache_key = self.generate_cache_key(request, context)
        cached_result = self.policy_cache.get(cache_key)
        if cached_result and not cached_result.is_expired():
            return cached_result.decision
        
        # Evaluate through policy layers
        evaluation_result = {
            "request_id": request.get("request_id"),
            "timestamp": time.time(),
            "context": context,
            "layer_results": {},
            "final_decision": "allow",
            "applied_policies": [],
            "confidence_score": 1.0
        }
        
        # Process through each layer
        for layer_name, layer in self.policy_layers.items():
            layer_result = layer.evaluate(request, context)
            evaluation_result["layer_results"][layer_name] = layer_result
            
            # Update final decision based on layer result
            if layer_result["decision"] == "deny":
                evaluation_result["final_decision"] = "deny"
                evaluation_result["confidence_score"] *= layer_result.get("confidence", 1.0)
            elif layer_result["decision"] == "conditional":
                evaluation_result["final_decision"] = "conditional"
                evaluation_result["conditions"] = evaluation_result.get("conditions", [])
                evaluation_result["conditions"].extend(layer_result.get("conditions", []))
        
        # Cache the result
        self.policy_cache.put(cache_key, evaluation_result, ttl=300)  # 5-minute TTL
        
        return evaluation_result

class SystemPolicyLayer(BasePolicyLayer):
    """System-level policies for resource management and system integrity."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.resource_policies = self.load_resource_policies()
        self.security_policies = self.load_security_policies()
        
    def evaluate(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate system-level policies."""
        result = {
            "layer": "system",
            "decision": "allow",
            "policies_evaluated": [],
            "violations": [],
            "recommendations": []
        }
        
        # Check resource availability
        if request.get("resource_request"):
            resource_result = self.evaluate_resource_policies(request["resource_request"], context)
            result["policies_evaluated"].append("resource_management")
            
            if not resource_result["allowed"]:
                result["decision"] = "deny"
                result["violations"].append({
                    "policy": "resource_limits",
                    "violation": resource_result["violation"],
                    "current_usage": resource_result["current_usage"],
                    "requested": resource_result["requested"],
                    "limit": resource_result["limit"]
                })
        
        # Check system security policies
        security_result = self.evaluate_security_policies(request, context)
        result["policies_evaluated"].append("system_security")
        
        if not security_result["allowed"]:
            result["decision"] = "deny"
            result["violations"].extend(security_result["violations"])
        
        return result
    
    def evaluate_resource_policies(self, resource_request: Dict[str, Any], 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate resource allocation policies."""
        current_usage = context.get("system_resources", {})
        
        for resource_type, requested_amount in resource_request.items():
            current_amount = current_usage.get(resource_type, 0)
            limit = self.resource_policies.get(resource_type, {}).get("max_allocation", float('inf'))
            
            if current_amount + requested_amount > limit:
                return {
                    "allowed": False,
                    "violation": f"Resource limit exceeded for {resource_type}",
                    "current_usage": current_amount,
                    "requested": requested_amount,
                    "limit": limit
                }
        
        return {"allowed": True}

class ExperimentPolicyLayer(BasePolicyLayer):
    """Experiment-specific policies for FL training governance."""
    
    def evaluate(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate experiment-level policies."""
        result = {
            "layer": "experiment",
            "decision": "allow",
            "policies_evaluated": [],
            "conditions": []
        }
        
        experiment_context = context.get("current_experiment", {})
        
        # Evaluate training policies
        if request.get("action") == "start_training":
            training_result = self.evaluate_training_policies(request, experiment_context)
            result["policies_evaluated"].append("training_governance")
            
            if training_result["conditions"]:
                result["decision"] = "conditional"
                result["conditions"].extend(training_result["conditions"])
        
        # Evaluate data policies
        if request.get("data_access"):
            data_result = self.evaluate_data_policies(request["data_access"], experiment_context)
            result["policies_evaluated"].append("data_governance")
            
            if not data_result["allowed"]:
                result["decision"] = "deny"
                result["violations"] = data_result["violations"]
        
        return result
```

### Dynamic Policy Adaptation

Implement policies that adapt based on system state:

```python
class AdaptivePolicyManager:
    """
    Manager for policies that adapt based on system state and learning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adaptive_policies = {}
        self.learning_history = {}
        self.adaptation_strategies = self.load_adaptation_strategies()
        
    def register_adaptive_policy(self, policy_id: str, policy_config: Dict[str, Any]):
        """Register a new adaptive policy."""
        self.adaptive_policies[policy_id] = AdaptivePolicy(policy_config)
        self.learning_history[policy_id] = []
    
    def update_policy_based_on_feedback(self, policy_id: str, 
                                      decision_context: Dict[str, Any],
                                      outcome: Dict[str, Any]):
        """Update policy parameters based on decision outcomes."""
        if policy_id not in self.adaptive_policies:
            return
            
        policy = self.adaptive_policies[policy_id]
        
        # Record the decision and its outcome
        feedback_record = {
            "timestamp": time.time(),
            "context": decision_context,
            "decision": decision_context.get("decision"),
            "outcome": outcome,
            "success": outcome.get("success", False)
        }
        
        self.learning_history[policy_id].append(feedback_record)
        
        # Adapt policy if enough feedback is available
        if len(self.learning_history[policy_id]) >= policy.min_feedback_samples:
            self.adapt_policy_parameters(policy_id)
    
    def adapt_policy_parameters(self, policy_id: str):
        """Adapt policy parameters based on historical feedback."""
        policy = self.adaptive_policies[policy_id]
        history = self.learning_history[policy_id]
        
        # Calculate success rate for different parameter ranges
        parameter_performance = {}
        
        for record in history[-policy.adaptation_window:]:
            param_key = self.discretize_parameters(record["context"]["parameters"])
            if param_key not in parameter_performance:
                parameter_performance[param_key] = {"successes": 0, "total": 0}
            
            parameter_performance[param_key]["total"] += 1
            if record["success"]:
                parameter_performance[param_key]["successes"] += 1
        
        # Find best performing parameters
        best_params = max(parameter_performance.items(),
                         key=lambda x: x[1]["successes"] / x[1]["total"] if x[1]["total"] > 0 else 0)
        
        # Update policy parameters
        new_params = self.undiscretize_parameters(best_params[0])
        policy.update_parameters(new_params)
        
        logger.info(f"Adapted policy {policy_id} parameters: {new_params}")
```

## Performance Optimization

### Resource Allocation Strategies

Implement sophisticated resource allocation:

```python
class ResourceAllocationOptimizer:
    """
    Optimize resource allocation across the federated learning system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.allocation_strategies = {
            "fair_share": FairShareStrategy(),
            "performance_based": PerformanceBasedStrategy(),
            "priority_based": PriorityBasedStrategy(),
            "adaptive": AdaptiveStrategy()
        }
        self.current_strategy = config.get("default_strategy", "adaptive")
        
    def optimize_allocation(self, clients: List[Dict[str, Any]], 
                          available_resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize resource allocation across clients.
        """
        strategy = self.allocation_strategies[self.current_strategy]
        
        allocation_plan = strategy.allocate(clients, available_resources)
        
        # Validate allocation plan
        if self.validate_allocation(allocation_plan, available_resources):
            return allocation_plan
        else:
            # Fallback to fair share if allocation is invalid
            return self.allocation_strategies["fair_share"].allocate(clients, available_resources)
    
    def validate_allocation(self, allocation_plan: Dict[str, Any], 
                          available_resources: Dict[str, Any]) -> bool:
        """Validate that allocation plan doesn't exceed available resources."""
        total_allocated = {}
        
        for client_id, allocation in allocation_plan["allocations"].items():
            for resource_type, amount in allocation.items():
                total_allocated[resource_type] = total_allocated.get(resource_type, 0) + amount
        
        for resource_type, total_amount in total_allocated.items():
            if total_amount > available_resources.get(resource_type, 0):
                return False
        
        return True

class AdaptiveStrategy:
    """Adaptive resource allocation based on client performance and needs."""
    
    def allocate(self, clients: List[Dict[str, Any]], 
                available_resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Allocate resources adaptively based on client characteristics.
        """
        allocation_plan = {
            "strategy": "adaptive",
            "timestamp": time.time(),
            "allocations": {},
            "optimization_objective": "maximize_system_efficiency"
        }
        
        # Calculate client scores based on multiple factors
        client_scores = []
        for client in clients:
            score = self.calculate_client_score(client)
            client_scores.append((client["client_id"], score))
        
        # Sort clients by score (highest first)
        client_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Allocate resources proportionally to scores
        total_score = sum(score for _, score in client_scores)
        
        for client_id, score in client_scores:
            allocation_ratio = score / total_score
            client_allocation = {}
            
            for resource_type, total_amount in available_resources.items():
                allocated_amount = total_amount * allocation_ratio
                client_allocation[resource_type] = allocated_amount
            
            allocation_plan["allocations"][client_id] = client_allocation
        
        return allocation_plan
    
    def calculate_client_score(self, client: Dict[str, Any]) -> float:
        """Calculate a composite score for client resource allocation priority."""
        # Factors: performance history, data quality, reliability, resource efficiency
        
        performance_score = client.get("historical_performance", {}).get("average_accuracy", 0.5)
        data_quality_score = client.get("data_profile", {}).get("quality_score", 0.5)
        reliability_score = client.get("reliability_metrics", {}).get("uptime_ratio", 0.8)
        efficiency_score = client.get("resource_efficiency", {}).get("computation_per_watt", 0.5)
        
        # Weighted combination
        composite_score = (
            0.3 * performance_score +
            0.25 * data_quality_score +
            0.25 * reliability_score +
            0.2 * efficiency_score
        )
        
        return composite_score
```

### System Tuning

Implement comprehensive system tuning:

```yaml
# configs/advanced/system_tuning.yaml
system_optimization:
  # Memory management
  memory:
    garbage_collection:
      strategy: "generational"
      gc_threshold: 0.8
      max_heap_size: "4g"
    
    caching:
      model_cache_size: "1g"
      data_cache_size: "2g"
      policy_cache_ttl: 300
      
  # Network optimization  
  network:
    connection_pooling:
      max_connections: 100
      connection_timeout: 30
      keepalive_timeout: 60
    
    compression:
      enabled: true
      algorithm: "lz4"
      compression_level: 3
      
    buffering:
      send_buffer_size: "64k"
      receive_buffer_size: "64k"
      
  # Computation optimization
  computation:
    thread_pool_size: 16
    async_workers: 8
    batch_processing:
      enabled: true
      batch_size: 32
      max_wait_time: 100
      
  # Storage optimization
  storage:
    database:
      connection_pool_size: 20
      query_timeout: 30
      batch_insert_size: 1000
      
    file_system:
      io_buffer_size: "1m"
      async_io: true
      compression: "gzip"
```

## Integration Patterns

### Event-Driven Architecture

Implement sophisticated event-driven patterns:

```python
class EventDrivenIntegrationManager:
    """
    Manage event-driven integration between FLOPY-NET components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_bus = EventBus()
        self.event_handlers = {}
        self.event_filters = {}
        self.integration_patterns = self.setup_integration_patterns()
        
    def setup_integration_patterns(self) -> Dict[str, Any]:
        """Setup different integration patterns."""
        return {
            "publish_subscribe": PublishSubscribePattern(self.event_bus),
            "event_sourcing": EventSourcingPattern(self.event_bus),
            "saga_pattern": SagaPattern(self.event_bus),
            "circuit_breaker": CircuitBreakerPattern(self.event_bus)
        }
    
    def register_event_handler(self, event_type: str, handler: callable,
                             filter_conditions: Dict[str, Any] = None):
        """Register an event handler with optional filtering."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        
        if filter_conditions:
            self.event_filters[f"{event_type}_{len(self.event_handlers[event_type])}"] = filter_conditions
    
    def publish_event(self, event: Dict[str, Any]):
        """Publish an event to the system."""
        event_type = event.get("type")
        
        # Apply filters and route to appropriate handlers
        for handler in self.event_handlers.get(event_type, []):
            if self.should_handle_event(event, handler):
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error handling event {event_type}: {e}")
                    
    def should_handle_event(self, event: Dict[str, Any], handler: callable) -> bool:
        """Determine if a handler should process an event based on filters."""
        # Implementation of event filtering logic
        return True  # Simplified for brevity

# Example: FL Training Event Handler
class FLTrainingEventHandler:
    """Handle FL training-related events."""
    
    def __init__(self, fl_server, policy_engine, collector):
        self.fl_server = fl_server
        self.policy_engine = policy_engine
        self.collector = collector
        
    def handle_round_started(self, event: Dict[str, Any]):
        """Handle FL round started event."""
        round_number = event["round_number"]
        experiment_id = event["experiment_id"]
        
        # Notify policy engine
        self.policy_engine.notify_round_started(experiment_id, round_number)
        
        # Start metrics collection
        self.collector.start_round_metrics_collection(experiment_id, round_number)
        
        # Log the event
        logger.info(f"FL round {round_number} started for experiment {experiment_id}")
    
    def handle_client_joined(self, event: Dict[str, Any]):
        """Handle client joined event."""
        client_id = event["client_id"]
        client_info = event["client_info"]
        
        # Policy compliance check
        compliance_result = self.policy_engine.check_client_compliance(client_id, client_info)
        
        if not compliance_result["compliant"]:
            # Reject client
            self.fl_server.reject_client(client_id, compliance_result["violations"])
        else:
            # Accept client and start monitoring
            self.collector.start_client_monitoring(client_id)
            logger.info(f"Client {client_id} joined and monitoring started")
```

## Configuration Management

### Hierarchical Configuration System

```python
class HierarchicalConfigManager:
    """
    Manage hierarchical configuration with inheritance and overrides.
    """
    
    def __init__(self, config_paths: List[str]):
        self.config_hierarchy = self.load_config_hierarchy(config_paths)
        self.resolved_config = self.resolve_configuration()
        
    def load_config_hierarchy(self, config_paths: List[str]) -> List[Dict[str, Any]]:
        """Load configuration files in hierarchical order."""
        configs = []
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                        config = yaml.safe_load(f)
                    else:
                        config = json.load(f)
                    configs.append(config)
        
        return configs
    
    def resolve_configuration(self) -> Dict[str, Any]:
        """Resolve configuration hierarchy with proper inheritance."""
        resolved = {}
        
        # Apply configurations in order (later configs override earlier ones)
        for config in self.config_hierarchy:
            resolved = self.deep_merge(resolved, config)
        
        # Apply environment variable overrides
        resolved = self.apply_env_overrides(resolved)
        
        return resolved
    
    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
```

This advanced configuration tutorial demonstrates sophisticated techniques for:

1. **Custom FL Algorithms**: Implementing complex algorithms like FedProx with adaptive parameters
2. **Advanced Networking**: Multi-tier topologies and sophisticated traffic management
3. **Sophisticated Policies**: Multi-layer policies with adaptive behavior
4. **Performance Optimization**: Resource allocation and system tuning
5. **Integration Patterns**: Event-driven architectures and complex service coordination

These techniques enable researchers to create highly customized and optimized federated learning experiments that closely match real-world deployment scenarios.
