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

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioGNS3Config(BaseModel):
    """Model for GNS3 configuration in a scenario."""
    server_url: str
    project_name: str
    reset_project: Optional[bool] = True
    cleanup_action: Optional[str] = "stop"  # Options: "stop", "destroy", "none"


class ScenarioFederationConfig(BaseModel):
    """Model for federation configuration in a scenario."""
    rounds: int
    local_epochs: int
    batch_size: int
    learning_rate: float
    optimizer: str
    loss: str
    metrics: List[str]


class ScenarioModelLayer(BaseModel):
    """Model for a neural network layer in a scenario model."""
    type: str
    filters: Optional[int] = None
    kernel_size: Optional[int] = None
    activation: Optional[str] = None
    pool_size: Optional[int] = None
    units: Optional[int] = None


class ScenarioModelConfig(BaseModel):
    """Model for model configuration in a scenario."""
    type: str
    input_shape: List[int]
    layers: List[ScenarioModelLayer]


class ScenarioDataConfig(BaseModel):
    """Model for data configuration in a scenario."""
    dataset: str
    classes: int
    distribution: str
    split: List[float]


class ScenarioMonitoringConfig(BaseModel):
    """Model for monitoring configuration in a scenario."""
    log_level: str
    metrics_interval: int
    save_model: bool
    save_history: bool


class ScenarioNetworkConfig(BaseModel):
    """Model for network configuration in a scenario."""
    topology_file: str
    use_static_ip: bool
    host_mapping: bool
    subnet: str
    gns3_network: bool
    wait_for_network: bool
    network_timeout: int
    ip_map: Dict[str, str]


class ScenarioResultsConfig(BaseModel):
    """Model for results configuration in a scenario."""
    output_dir: str
    save_format: str
    metrics: List[str]


class Scenario(BaseModel):
    """Model for a complete scenario."""
    scenario_type: str
    scenario_name: str
    description: str
    gns3: ScenarioGNS3Config
    federation: ScenarioFederationConfig
    model: ScenarioModelConfig
    data: ScenarioDataConfig
    monitoring: ScenarioMonitoringConfig
    network: ScenarioNetworkConfig
    results: ScenarioResultsConfig
    training_timeout: int


class ScenarioSummary(BaseModel):
    """Summary model for listing scenarios."""
    scenario_type: str
    scenario_name: str
    description: str
    gns3_project_name: str
    config_file_path: str
    status: Optional[str] = None  # e.g., "running", "stopped", "not_started"


class ScenarioList(BaseModel):
    """Response model for listing scenarios."""
    scenarios: List[ScenarioSummary] 