# Build and start the containers
docker-compose up -d

# Check if the services are running
Write-Host "Waiting for services to start..."
Start-Sleep -Seconds 10

# Check Policy Engine
Write-Host "Checking Policy Engine..."
try {
    Invoke-RestMethod -Uri "http://localhost:8000/" -ErrorAction Stop | Out-Null
    Write-Host "Policy Engine is running"
} catch {
    Write-Host "Policy Engine is not responding"
}

# Check Dashboard
Write-Host "Checking Dashboard..."
try {
    Invoke-RestMethod -Uri "http://localhost:8050/" -ErrorAction Stop | Out-Null
    Write-Host "Dashboard is running"
} catch {
    Write-Host "Dashboard is not responding"
}

# Check Dashboard API
Write-Host "Checking Dashboard API..."
try {
    Invoke-RestMethod -Uri "http://localhost:8051/" -ErrorAction Stop | Out-Null
    Write-Host "Dashboard API is running"
} catch {
    Write-Host "Dashboard API is not responding"
}

Write-Host ""
Write-Host "Access the dashboard at: http://localhost:8050/"
Write-Host "Access the policy engine API at: http://localhost:8000/"
Write-Host "Access the ONOS web UI at: http://localhost:8181/onos/ui/"
Write-Host ""
Write-Host "To stop the services:"
Write-Host "docker-compose down" 