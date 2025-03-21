"""
Simulation API Module

This module provides RESTful API endpoints for running and managing
federated learning simulations.
"""
import logging
import time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Body, Query, Path, Depends

from src.service.simulation_runner import SimulationRunner
from src.domain.scenarios.scenario_registry import ScenarioRegistry

# Configure logging
logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(
    prefix="/api/simulations",
    tags=["simulations"],
    responses={404: {"description": "Not found"}},
)

# Initialize services
simulation_runner = SimulationRunner()
scenario_registry = ScenarioRegistry()


@router.get("/scenarios", response_model=List[Dict[str, str]])
async def list_scenarios():
    """
    List all available simulation scenarios.
    
    Returns:
        List of scenario information including name and description
    """
    scenarios = scenario_registry.get_scenario_info()
    return scenarios


@router.get("/scenarios/{scenario_name}", response_model=Dict[str, Any])
async def get_scenario_details(scenario_name: str = Path(..., description="The name of the scenario")):
    """
    Get detailed information about a specific scenario.
    
    Args:
        scenario_name: The name of the scenario
        
    Returns:
        Detailed scenario information
    """
    scenario = scenario_registry.get_scenario(scenario_name)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")
    
    return {
        "name": scenario.get_name(),
        "description": scenario.get_description(),
        "topology": scenario.get_topology_config(),
        "server_config": scenario.get_server_config(),
        "client_configs": scenario.get_client_configs(),
        "sdn_policies": scenario.get_sdn_policies(),
        "network_conditions": scenario.get_network_conditions(),
        "simulation_events": scenario.get_simulation_events(),
        "expected_metrics": scenario.get_expected_metrics()
    }


@router.post("/", response_model=Dict[str, Any])
async def start_simulation(
    scenario_name: str = Body(..., description="The name of the scenario to run"),
    simulation_id: Optional[str] = Body(None, description="Optional custom ID for the simulation"),
    config_overrides: Optional[Dict[str, Any]] = Body(None, description="Optional configuration overrides"),
    policy_config: Optional[Dict[str, Any]] = Body(None, description="Optional policy configuration overrides")
):
    """
    Start a new simulation.
    
    Args:
        scenario_name: The name of the scenario to run
        simulation_id: Optional custom ID for the simulation
        config_overrides: Optional configuration overrides
        policy_config: Optional policy configuration overrides
        
    Returns:
        Information about the started simulation
    """
    # Start the simulation
    sim_id = simulation_runner.start_simulation(
        scenario_name=scenario_name,
        simulation_id=simulation_id,
        config_overrides=config_overrides,
        policy_config=policy_config
    )
    
    if not sim_id:
        raise HTTPException(status_code=400, detail="Failed to start simulation")
    
    # Wait a moment for the simulation to initialize
    time.sleep(0.5)
    
    # Get the simulation info
    sim_info = simulation_runner.get_simulation_info(sim_id)
    
    return {
        "message": "Simulation started successfully",
        "simulation_id": sim_id,
        "status": sim_info["status"],
        "start_time": sim_info["start_time"]
    }


@router.get("/", response_model=List[Dict[str, Any]])
async def list_simulations():
    """
    List all simulations.
    
    Returns:
        List of simulation information
    """
    simulations = simulation_runner.list_simulations()
    return simulations


@router.get("/{simulation_id}", response_model=Dict[str, Any])
async def get_simulation(
    simulation_id: str = Path(..., description="The ID of the simulation")
):
    """
    Get information about a specific simulation.
    
    Args:
        simulation_id: The ID of the simulation
        
    Returns:
        Detailed simulation information
    """
    simulation = simulation_runner.get_simulation_info(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    
    return simulation


@router.post("/{simulation_id}/stop", response_model=Dict[str, Any])
async def stop_simulation(
    simulation_id: str = Path(..., description="The ID of the simulation to stop")
):
    """
    Stop a running simulation.
    
    Args:
        simulation_id: The ID of the simulation to stop
        
    Returns:
        Status information
    """
    success = simulation_runner.stop_simulation(simulation_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to stop simulation '{simulation_id}'")
    
    # Get updated simulation info
    simulation = simulation_runner.get_simulation_info(simulation_id)
    
    return {
        "message": "Simulation stopped successfully",
        "simulation_id": simulation_id,
        "status": simulation["status"]
    }


@router.get("/{simulation_id}/metrics", response_model=Dict[str, Any])
async def get_simulation_metrics(
    simulation_id: str = Path(..., description="The ID of the simulation")
):
    """
    Get metrics for a specific simulation.
    
    Args:
        simulation_id: The ID of the simulation
        
    Returns:
        Simulation metrics
    """
    simulation = simulation_runner.get_simulation_info(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    
    return {
        "simulation_id": simulation_id,
        "status": simulation["status"],
        "metrics": simulation["metrics"]
    } 