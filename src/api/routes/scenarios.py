"""
Simulation Scenarios API

This module provides API endpoints for managing and executing simulation scenarios
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.domain.scenarios.scenario_registry import ScenarioRegistry
from src.service.simulation_runner import SimulationRunner

router = APIRouter(
    prefix="/scenarios",
    tags=["scenarios"],
    responses={404: {"description": "Not found"}},
)

class ScenarioInfo(BaseModel):
    """Basic information about a scenario"""
    name: str
    display_name: str
    description: str

class ScenarioDetail(BaseModel):
    """Detailed information about a scenario configuration"""
    name: str
    display_name: str
    description: str
    topology_config: Dict[str, Any]
    server_config: Dict[str, Any]
    client_count: int
    sdn_policy_count: int
    network_condition_count: int
    simulation_event_count: int
    expected_metrics: Dict[str, Any]

class CustomScenarioConfig(BaseModel):
    """Custom configuration for a simulation scenario"""
    scenario_name: str = Field(..., description="The name of the base scenario to customize")
    config_overrides: Dict[str, Any] = Field(default={}, description="Configuration overrides to apply")

class SimulationResponse(BaseModel):
    """Response from starting a simulation"""
    simulation_id: str
    status: str
    message: str

class SimulationMetrics(BaseModel):
    """Metrics from a simulation run"""
    simulation_id: str
    status: str
    fl_performance: Dict[str, Any]
    network_performance: Dict[str, Any]
    custom_metrics: Optional[Dict[str, Any]] = None

@router.get("/", response_model=List[ScenarioInfo])
async def list_scenarios():
    """
    List all available simulation scenarios
    """
    registry = ScenarioRegistry()
    return registry.get_scenario_info()

@router.get("/{scenario_name}", response_model=ScenarioDetail)
async def get_scenario(scenario_name: str):
    """
    Get detailed information about a specific scenario
    """
    registry = ScenarioRegistry()
    scenario = registry.get_scenario(scenario_name)
    
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")
    
    return {
        "name": scenario_name,
        "display_name": scenario.get_name(),
        "description": scenario.get_description(),
        "topology_config": scenario.get_topology_config(),
        "server_config": scenario.get_server_config(),
        "client_count": len(scenario.get_client_configs()),
        "sdn_policy_count": len(scenario.get_sdn_policies()),
        "network_condition_count": len(scenario.get_network_conditions()),
        "simulation_event_count": len(scenario.get_simulation_events()),
        "expected_metrics": scenario.get_expected_metrics()
    }

@router.post("/run", response_model=SimulationResponse)
async def run_simulation(
    scenario_name: str = Query(..., description="Name of the scenario to run"),
    config_overrides: Dict[str, Any] = Body(default={}, description="Optional configuration overrides"),
    duration_seconds: int = Query(3600, description="Duration to run the simulation"),
    collect_metrics: bool = Query(True, description="Whether to collect metrics during the simulation")
):
    """
    Run a simulation with the specified scenario
    """
    registry = ScenarioRegistry()
    scenario = registry.get_scenario(scenario_name, config_overrides)
    
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")
    
    # Initialize simulation runner
    runner = SimulationRunner()
    
    # Start the simulation
    simulation_id = runner.start_simulation(
        scenario=scenario,
        duration_seconds=duration_seconds,
        collect_metrics=collect_metrics
    )
    
    return {
        "simulation_id": simulation_id,
        "status": "started",
        "message": f"Simulation started with scenario '{scenario_name}'"
    }

@router.post("/run_custom", response_model=SimulationResponse)
async def run_custom_simulation(
    custom_config: CustomScenarioConfig,
    duration_seconds: int = Query(3600, description="Duration to run the simulation"),
    collect_metrics: bool = Query(True, description="Whether to collect metrics during the simulation")
):
    """
    Run a simulation with a custom scenario configuration
    """
    registry = ScenarioRegistry()
    scenario = registry.get_scenario(custom_config.scenario_name, custom_config.config_overrides)
    
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{custom_config.scenario_name}' not found")
    
    # Initialize simulation runner
    runner = SimulationRunner()
    
    # Start the simulation
    simulation_id = runner.start_simulation(
        scenario=scenario,
        duration_seconds=duration_seconds,
        collect_metrics=collect_metrics
    )
    
    return {
        "simulation_id": simulation_id,
        "status": "started",
        "message": f"Custom simulation started with base scenario '{custom_config.scenario_name}'"
    }

@router.get("/status/{simulation_id}", response_model=Dict[str, Any])
async def get_simulation_status(simulation_id: str):
    """
    Get the status of a running simulation
    """
    runner = SimulationRunner()
    status = runner.get_simulation_status(simulation_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Simulation with ID '{simulation_id}' not found")
    
    return status

@router.get("/metrics/{simulation_id}", response_model=SimulationMetrics)
async def get_simulation_metrics(simulation_id: str):
    """
    Get metrics from a simulation run
    """
    runner = SimulationRunner()
    metrics = runner.get_simulation_metrics(simulation_id)
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for simulation with ID '{simulation_id}' not found")
    
    return metrics

@router.post("/stop/{simulation_id}")
async def stop_simulation(simulation_id: str):
    """
    Stop a running simulation
    """
    runner = SimulationRunner()
    success = runner.stop_simulation(simulation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Simulation with ID '{simulation_id}' not found or already stopped")
    
    return {"status": "stopped", "message": f"Simulation '{simulation_id}' stopped successfully"} 