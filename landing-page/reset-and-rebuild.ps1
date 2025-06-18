# Reset and rebuild the Docker container for the landing page

Write-Host "Stopping and removing any existing container..." -ForegroundColor Cyan
docker stop flopynet-landing-page 2>$null
docker rm flopynet-landing-page 2>$null

Write-Host "`nBuilding the image from scratch..." -ForegroundColor Cyan
docker-compose build --no-cache

Write-Host "`nStarting the container..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "`nWaiting 5 seconds for container to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "`nChecking container status..." -ForegroundColor Cyan
docker ps | Select-String "flopynet-landing-page"

Write-Host "`nAttempting to open the site in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8080"

Write-Host "`nIf you still can't access the site, run .\troubleshoot.ps1" -ForegroundColor Yellow
