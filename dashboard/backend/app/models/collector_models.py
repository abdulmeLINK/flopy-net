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

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Enum for different metric types."""
    FL_SERVER = "fl_server"
    POLICY_ENGINE = "policy_engine"
    NETWORK = "network"


class BaseMetric(BaseModel):
    """Base model for all metrics."""
    timestamp: str
    type: str
    data: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    status: str
    count: int
    offset: Optional[int] = 0
    limit: Optional[int] = 100
    total: Optional[int] = None
    metrics: List[BaseMetric]


class LatestMetricResponse(BaseModel):
    """Response model for latest metrics endpoint."""
    status: str = "success"
    timestamp: str = ""
    metrics: Optional[Dict[str, Any]] = None


class FLMetricData(BaseModel):
    """Data model specifically for FL metrics."""
    current_round: Optional[int] = None
    total_rounds: Optional[int] = None
    connected_clients: Optional[int] = None
    accuracy: Optional[float] = None
    loss: Optional[float] = None
    aggregate_fit_count: Optional[int] = None
    status: Optional[str] = None


class FLMetric(BaseModel):
    """Model for FL metrics."""
    timestamp: str
    round: int = 0
    accuracy: float = 0.0
    loss: float = 0.0
    clients_connected: int = 0
    clients_total: int = 0
    training_complete: bool = False
    model_size_mb: Optional[float] = 0.0
    data_state: Optional[str] = "initializing"  # One of "error", "active_training", "initializing", "training_complete"
    raw_metrics: Optional[Dict[str, Any]] = None


class FLMetricsResponse(BaseModel):
    """Response model for FL metrics endpoint."""
    metrics: List[Dict[str, Any]]
    count: int = 0
    status: str = "success"


class PolicyDecision(BaseModel):
    """Model for policy decisions."""
    decision_id: str
    timestamp: str
    component: str
    action: str
    allowed: bool
    reason: Optional[str] = None


class PolicyDecisionsResponse(BaseModel):
    """Response model for policy decisions endpoint."""
    status: str
    count: int
    decisions: List[PolicyDecision]


class Event(BaseModel):
    """Model for system events."""
    event_id: Optional[str] = None
    timestamp: str
    source_component: Optional[str] = "unknown"
    event_type: Optional[str] = "info"
    level: Optional[str] = "info"
    message: Optional[str] = ""
    details: Optional[Dict[str, Any]] = None


class EventsResponse(BaseModel):
    """Response model for events endpoint."""
    events: List[Event]
    total: int
    limit: int
    offset: int


class MonitoringStatus(BaseModel):
    """Model for monitoring status."""
    status: str
    timestamp: str
    services: Dict[str, str]  # service_name -> status
    last_collection: Dict[str, str]  # metric_type -> timestamp


class FrontendMetricQuery(BaseModel):
    metric_types: List[str]
    start_time: str
    end_time: str
    components: Optional[List[str]] = None
    aggregation: str # 'avg' | 'min' | 'max' | 'sum' | 'count'
    interval: str 