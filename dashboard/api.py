"""
REST API for the FL-SDN Dashboard
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
import time

from fastapi import FastAPI, HTTPException, Query, Body, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import scenario manager
from .scenarios import scenario_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard-api")

# Create FastAPI app
app = FastAPI(
    title="FL-SDN Dashboard API",
    description="REST API for the Federated Learning and SDN Integration Dashboard",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class StatusResponse(BaseModel):
    status: str = "success"
    message: str


class MetricsResponse(BaseModel):
    timestamp: str
    metrics: Dict[str, Any]


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    active: bool


# API Routes
@app.get("/", response_model=StatusResponse)
async def root():
    """Root endpoint returns API status."""
    return {"status": "success", "message": "FL-SDN Dashboard API is running"}


@app.get("/fl/metrics", response_model=MetricsResponse)
async def get_fl_metrics():
    """Get Federated Learning metrics."""
    try:
        metrics = scenario_manager.get_fl_metrics()
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error getting FL metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get FL metrics: {str(e)}"
        )


@app.get("/network/metrics", response_model=MetricsResponse)
async def get_network_metrics():
    """Get network metrics from the SDN controller."""
    try:
        metrics = scenario_manager.get_network_metrics()
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error getting network metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get network metrics: {str(e)}"
        )


@app.get("/policies", response_model=MetricsResponse)
async def get_policies():
    """Get active policies and execution history."""
    try:
        policy_data = scenario_manager.get_policy_metrics()
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": policy_data
        }
    except Exception as e:
        logger.error(f"Error getting policy data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get policy data: {str(e)}"
        )


@app.get("/app/metrics", response_model=MetricsResponse)
async def get_app_metrics():
    """Get application-specific metrics for the current scenario."""
    try:
        app_metrics = scenario_manager.get_app_metrics()
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": app_metrics
        }
    except Exception as e:
        logger.error(f"Error getting application metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get application metrics: {str(e)}"
        )


@app.get("/scenarios/list", response_model=List[ScenarioResponse])
async def list_scenarios():
    """List available simulation scenarios."""
    try:
        scenarios = []
        for scenario_id, name in scenario_manager.scenario_names.items():
            scenarios.append({
                "id": scenario_id,
                "name": name,
                "description": scenario_manager.scenario_descriptions[scenario_id],
                "active": scenario_id == scenario_manager.current_scenario
            })
        return scenarios
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scenarios: {str(e)}"
        )


@app.post("/scenarios/set/{scenario_id}", response_model=StatusResponse)
async def set_scenario(scenario_id: str):
    """Set the active simulation scenario."""
    try:
        if scenario_id not in scenario_manager.scenarios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{scenario_id}' not found"
            )
        
        scenario_manager.set_scenario(scenario_id)
        return {
            "status": "success",
            "message": f"Scenario set to '{scenario_manager.scenario_names[scenario_id]}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting scenario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set scenario: {str(e)}"
        )


@app.get("/metrics/all", response_model=MetricsResponse)
async def get_all_metrics():
    """Get all metrics for the dashboard in a single call."""
    try:
        # Refresh scenario data
        scenario_manager.refresh_data()
        
        # Get all metrics
        all_metrics = scenario_manager.get_all_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": all_metrics
        }
    except Exception as e:
        logger.error(f"Error getting all metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all metrics: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8051) 