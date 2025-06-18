# Docker run script for Windows
Write-Host "Starting Docker services..." -ForegroundColor Cyan

# Make sure logs directory exists
$logDirs = @(
    "logs/policy-engine",
    "logs/fl-server",
    "logs/collector",
    "logs/sdn-controller",
    "logs/ovs"
)

foreach ($dir in $logDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}

# Build images if needed
Write-Host "Building Docker images..." -ForegroundColor Cyan
docker-compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build images. See error above." -ForegroundColor Red
    exit 1
}

# Start the containers
Write-Host "Starting containers..." -ForegroundColor Cyan
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start containers. See error above." -ForegroundColor Red
    exit 1
}

# Display container status
Write-Host "`nContainer status:" -ForegroundColor Green
docker-compose ps

Write-Host "`nTo view logs for a specific service:" -ForegroundColor Yellow
Write-Host "  docker-compose logs -f [service-name]" -ForegroundColor White
Write-Host "  Example: docker-compose logs -f policy-engine" -ForegroundColor White

Write-Host "`nTo stop all services:" -ForegroundColor Yellow
Write-Host "  docker-compose down" -ForegroundColor White

# Give containers time to initialize
Write-Host "Waiting for services to start..."
Start-Sleep -Seconds 30

# Check the status of the containers
Write-Host "Container Status:"
docker-compose ps

# Check health
Write-Host "Container Health:"
docker inspect --format "{{.State.Health.Status}}" policy-engine
docker inspect --format "{{.State.Health.Status}}" fl-server
docker inspect --format "{{.State.Health.Status}}" collector
docker inspect --format "{{.State.Health.Status}}" sdn-controller
docker inspect --format "{{.State.Health.Status}}" ovs-1

# Function to save logs
function Save-Logs {
    param($ContainerName)
    
    Write-Host "Saving logs for $ContainerName..."
    docker logs $ContainerName > "logs/$ContainerName/container.log" 2>&1
}

# Save logs for each container
Save-Logs -ContainerName "policy-engine"
Save-Logs -ContainerName "fl-server"
Save-Logs -ContainerName "collector"
Save-Logs -ContainerName "sdn-controller" 
Save-Logs -ContainerName "ovs-1"

Write-Host "Container logs have been saved to logs/ directory"
Write-Host ""

# Check if policy-engine is accessible
Write-Host "Testing policy-engine API:"
try {
    Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get
} catch {
    Write-Host "Policy engine health check failed"
}
Write-Host ""

# Check if FL server is accessible
Write-Host "Testing FL server health:"
try {
    Invoke-RestMethod -Uri "http://localhost:8082/health" -Method Get
} catch {
    Write-Host "FL server health check failed"
}
Write-Host ""

# Check if collector is accessible
Write-Host "Testing collector API:"
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
} catch {
    Write-Host "Collector health check failed"
}
Write-Host ""

Write-Host "Done" 