"""
Dashboard API

This module provides a REST API for the dashboard.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Dashboard API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data
fl_metrics = {
    "rounds": 10,
    "accuracy": [0.5, 0.55, 0.6, 0.65, 0.7, 0.72, 0.75, 0.78, 0.8, 0.82],
    "loss": [1.0, 0.9, 0.8, 0.7, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35],
    "clients": 5,
}

network_metrics = {
    "nodes": 10,
    "links": 15,
    "latency": {
        "avg": 45.5,
        "min": 10.2,
        "max": 95.7,
    },
    "bandwidth": {
        "avg": 120.5,
        "min": 50.3,
        "max": 200.1,
    },
}

policies = [
    {
        "id": 1,
        "name": "High Latency Rerouting",
        "type": "SDN",
        "status": "Active",
    },
    {
        "id": 2,
        "name": "High Trust Node Selection",
        "type": "FL",
        "status": "Active",
    },
    {
        "id": 3,
        "name": "Anomaly Detection",
        "type": "Security",
        "status": "Standby",
    },
]


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Dashboard API", "version": "1.0.0"}


@app.get("/fl/metrics")
async def get_fl_metrics():
    """Get FL metrics."""
    return fl_metrics


@app.get("/network/metrics")
async def get_network_metrics():
    """Get network metrics."""
    return network_metrics


@app.get("/policies")
async def get_policies():
    """Get policies."""
    return policies


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8051) 