#!/bin/bash

# Build and start the containers
docker-compose up -d

# Check if the services are running
echo "Waiting for services to start..."
sleep 10

# Check Policy Engine
echo "Checking Policy Engine..."
curl -s http://localhost:8000/ || echo "Policy Engine is not responding"

# Check Dashboard
echo "Checking Dashboard..."
curl -s http://localhost:8050/ || echo "Dashboard is not responding"

# Check Dashboard API
echo "Checking Dashboard API..."
curl -s http://localhost:8051/ || echo "Dashboard API is not responding"

echo "Access the dashboard at: http://localhost:8050/"
echo "Access the policy engine API at: http://localhost:8000/"
echo "Access the ONOS web UI at: http://localhost:8181/onos/ui/"

echo "To stop the services:"
echo "docker-compose down" 