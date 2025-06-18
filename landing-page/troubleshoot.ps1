# Troubleshooting script for the landing page Docker container

Write-Host "Checking if the container is running..." -ForegroundColor Cyan
docker ps -a | Select-String "flopynet-landing-page"

Write-Host "`nChecking container logs..." -ForegroundColor Cyan
docker logs flopynet-landing-page

Write-Host "`nTrying to access the site from within the container..." -ForegroundColor Cyan
docker exec flopynet-landing-page curl -s localhost

Write-Host "`nChecking container network..." -ForegroundColor Cyan
docker network inspect flopynet-network

Write-Host "`nChecking port bindings..." -ForegroundColor Cyan
docker port flopynet-landing-page

Write-Host "`nRestarting container..." -ForegroundColor Cyan
docker restart flopynet-landing-page

Write-Host "`nWaiting 5 seconds for container to restart..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host "`nChecking logs after restart..." -ForegroundColor Cyan
docker logs flopynet-landing-page

Write-Host "`nAttempting to open the site in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8080"
