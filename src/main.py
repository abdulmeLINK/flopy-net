"""
Federated Learning System - Main Application

This module serves as the entry point for the federated learning system.
It sets up the application components and starts the REST API server.
"""
import os
import sys
import logging
import argparse
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.services.server_service import ServerService
from src.application.services.client_service import ClientService
from src.domain.interfaces.policy_engine import IPolicyEngine
from src.domain.policy.rule_based_policy_engine import RuleBasedPolicyEngine
from src.infrastructure.repositories.in_memory_client_repository import InMemoryClientRepository
from src.infrastructure.repositories.file_model_repository import FileModelRepository
from src.infrastructure.config.config_manager import ConfigManager
from src.presentation.rest.api_app import ApiApp

# Import simulation components
from src.api.simulation_api import router as simulation_router
from src.domain.scenarios.scenario_registry import ScenarioRegistry
from src.domain.scenarios.urban_scenario import UrbanScenario
from src.domain.scenarios.industrial_iot_scenario import IndustrialIoTScenario
from src.domain.scenarios.healthcare_scenario import HealthcareScenario


def setup_logging(log_level: str) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('fl_system.log')
        ]
    )
    
    logger = logging.getLogger('federated_learning')
    logger.setLevel(numeric_level)
    
    return logger


def create_policy_engine(config: Dict[str, Any], logger: logging.Logger) -> IPolicyEngine:
    """
    Create and configure the policy engine.
    
    Args:
        config: Configuration dictionary
        logger: Logger instance
    
    Returns:
        Configured policy engine
    """
    policy_config = config.get('policy', {})
    enabled = policy_config.get('enabled', True)
    strategies_path = policy_config.get('strategies_path', './strategies')
    default_strategy = policy_config.get('default_strategy', 'default')
    
    logger.info(f"Creating policy engine (enabled={enabled})")
    
    policy_engine = RuleBasedPolicyEngine(
        enabled=enabled,
        logger=logger
    )
    
    # Ensure strategies directory exists
    os.makedirs(strategies_path, exist_ok=True)
    
    # Load strategies from directory
    policy_engine.load_strategies(strategies_path)
    
    # Set active strategy
    if default_strategy:
        policy_engine.set_active_strategy(default_strategy)
    
    return policy_engine


def create_app(config_path: str = None, mode: str = 'server', log_level: str = 'INFO') -> ApiApp:
    """
    Create and configure the API application.
    
    Args:
        config_path: Path to configuration file
        mode: Application mode ('server', 'client', or 'both')
        log_level: Log level
    
    Returns:
        Configured API application
    """
    # Set up logging
    logger = setup_logging(log_level)
    logger.info(f"Starting Federated Learning System in {mode} mode")
    
    # Load configuration
    config_manager = ConfigManager(config_path)
    config = config_manager.get_config()
    logger.info(f"Loaded configuration from {config_path if config_path else 'default'}")
    
    # Create policy engine
    policy_engine = create_policy_engine(config, logger)
    
    # Initialize application components and use cases
    server_use_case = None
    client_use_case = None
    
    # Set up server components if in server or both mode
    if mode in ['server', 'both']:
        # Create repositories
        model_repo_path = config.get('server', {}).get('model_repository_path', './models')
        os.makedirs(model_repo_path, exist_ok=True)
        
        client_repository = InMemoryClientRepository(logger=logger)
        model_repository = FileModelRepository(base_dir=model_repo_path, logger=logger)
        
        # Create server use case
        server_use_case = ServerService(
            client_repository=client_repository,
            model_repository=model_repository,
            policy_engine=policy_engine,
            logger=logger
        )
        
        logger.info("Server components initialized")
    
    # Set up client components if in client or both mode
    if mode in ['client', 'both']:
        # Create client use case with minimal dependencies
        client_use_case = ClientService(
            policy_engine=policy_engine,
            logger=logger
        )
        
        logger.info("Client components initialized")
    
    # Create API application
    app = ApiApp(
        server_use_case=server_use_case,
        client_use_case=client_use_case,
        policy_engine=policy_engine,
        logger=logger
    )
    
    logger.info("API application created")
    return app


def create_fastapi_app() -> FastAPI:
    """
    Create a FastAPI application with simulation capabilities.
    
    Returns:
        FastAPI application instance
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("federated_learning_simulations")
    
    # Create FastAPI app
    app = FastAPI(
        title="Federated Learning Simulation API",
        description="API for running federated learning simulations with different scenarios and policies",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register scenarios
    def register_scenarios():
        """Register all available simulation scenarios."""
        logger.info("Registering simulation scenarios")
        registry = ScenarioRegistry()
        registry.register_scenario(UrbanScenario)
        registry.register_scenario(IndustrialIoTScenario)
        registry.register_scenario(HealthcareScenario)
        logger.info(f"Registered {len(registry.get_scenario_names())} scenarios")
    
    # Include routers
    app.include_router(simulation_router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize components when the application starts."""
        logger.info("Starting Federated Learning Simulation API")
        register_scenarios()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources when the application shuts down."""
        logger.info("Shutting down Federated Learning Simulation API")
    
    # Root endpoint for health check
    @app.get("/", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "message": "Federated Learning Simulation API is running",
            "version": app.version
        }
    
    return app


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Federated Learning System')
    parser.add_argument('--config', '-c', type=str, help='Path to configuration file')
    parser.add_argument('--mode', '-m', type=str, choices=['server', 'client', 'both', 'simulation'], 
                        default='server', help='Application mode')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the API server on')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the API server on')
    parser.add_argument('--log-level', '-l', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    if args.mode == 'simulation':
        # Run FastAPI app for simulations
        import uvicorn
        app = create_fastapi_app()
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower())
    else:
        # Create and run regular API application
        app = create_app(config_path=args.config, mode=args.mode, log_level=args.log_level)
        app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main() 