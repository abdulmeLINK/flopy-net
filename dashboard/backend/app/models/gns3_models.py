from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GNS3Project(BaseModel):
    """Model for a GNS3 project."""
    project_id: str
    name: str
    status: Optional[str] = None  # e.g., "opened", "closed"
    path: Optional[str] = None
    auto_open: Optional[bool] = None
    auto_close: Optional[bool] = None
    auto_start: Optional[bool] = None


class GNS3ProjectSummary(BaseModel):
    """Summary model for listing GNS3 projects."""
    project_id: str
    name: str
    status: str


class GNS3ProjectList(BaseModel):
    """Response model for listing GNS3 projects."""
    projects: List[GNS3ProjectSummary]


class GNS3Node(BaseModel):
    """Model for a GNS3 node."""
    node_id: str
    name: str
    node_type: str  # e.g., "docker", "vpcs", "qemu"
    status: str  # e.g., "started", "stopped"
    console: Optional[int] = None
    console_host: Optional[str] = None
    x: Optional[int] = None  # X position in topology
    y: Optional[int] = None  # Y position in topology
    z: Optional[int] = None  # Z position (layer) in topology
    properties: Optional[Dict[str, Any]] = None  # May include service-specific details


class GNS3Link(BaseModel):
    """Model for a GNS3 link."""
    link_id: str
    nodes: List[Dict[str, Any]]  # List of connected nodes with adapter info
    link_type: Optional[str] = None
    bandwidth: Optional[int] = None  # in bps
    latency: Optional[int] = None  # in ms
    packet_loss: Optional[float] = None  # as percentage


class GNS3Topology(BaseModel):
    """Model for a GNS3 project topology."""
    project_id: str
    nodes: List[GNS3Node]
    links: List[GNS3Link]


class GNS3NodeCreate(BaseModel):
    """Model for creating a GNS3 node."""
    name: str
    node_type: str
    compute_id: Optional[str] = None
    template_id: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


class GNS3LinkCreate(BaseModel):
    """Model for creating a GNS3 link."""
    nodes: List[Dict[str, Any]]  # Format: [{"node_id": "...", "adapter_number": 0, "port_number": 0}, {...}]
    link_type: Optional[str] = None


class GNS3LinkUpdate(BaseModel):
    """Model for updating a GNS3 link."""
    bandwidth: Optional[int] = None  # in bps
    latency: Optional[int] = None  # in ms
    packet_loss: Optional[float] = None  # as percentage


class GNS3Template(BaseModel):
    """Model for a GNS3 template."""
    template_id: str
    name: str
    template_type: str  # e.g., "docker", "qemu"
    category: str
    symbol: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class GNS3TemplateList(BaseModel):
    """Response model for listing GNS3 templates."""
    templates: List[GNS3Template] 