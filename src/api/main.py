"""
Main API module for the federated learning service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, network, clients, server, scenarios

app = FastAPI(
    title="Federated Learning API",
    description="API for managing federated learning simulations",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(network.router)
app.include_router(clients.router)
app.include_router(server.router)
app.include_router(scenarios.router)

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Federated Learning API",
        "version": "0.1.0",
        "description": "API for managing federated learning simulations",
    } 