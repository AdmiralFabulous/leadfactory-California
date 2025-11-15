# Sim Startup Script
# This script starts Sim containers after Docker Desktop is ready

Write-Host "Starting Sim AI Agent Workflow Platform..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Change to Sim directory
Set-Location "C:\Users\LX\Documents\Project California\sim"

# Wait for Docker to be ready (up to 2 minutes)
Write-Host "`nWaiting for Docker Desktop to be ready..." -ForegroundColor Yellow
$maxAttempts = 60
$attempts = 0

while ($attempts -lt $maxAttempts) {
    $dockerStatus = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Docker is ready!" -ForegroundColor Green
        break
    } else {
        if ($attempts % 10 -eq 0) {
            Write-Host "`nStill waiting for Docker..." -ForegroundColor Yellow
        } else {
            Write-Host "." -NoNewline
        }
        Start-Sleep -Seconds 2
        $attempts++
    }
}

if ($attempts -eq $maxAttempts) {
    Write-Host "`n❌ Timeout waiting for Docker Desktop to start" -ForegroundColor Red
    Write-Host "Please start Docker Desktop manually and run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Sim containers
Write-Host "`nStarting Sim containers..." -ForegroundColor Yellow
$env:POSTGRES_PORT = "5433"
docker compose -f docker-compose.prod.yml up -d

# Wait a moment for containers to initialize
Start-Sleep -Seconds 5

# Check container status
Write-Host "`nChecking container status..." -ForegroundColor Yellow
$containers = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "sim-"

if ($containers) {
    Write-Host "`n✅ Sim is running successfully!" -ForegroundColor Green
    Write-Host "`nContainer Status:" -ForegroundColor Cyan
    $containers | ForEach-Object { Write-Host $_ }
    
    Write-Host "`n🚀 Sim is available at: http://localhost:3000" -ForegroundColor Green
    Write-Host "📡 Realtime server at: http://localhost:3002" -ForegroundColor Green
    Write-Host "🗄️  PostgreSQL at: localhost:5433" -ForegroundColor Green
} else {
    Write-Host "`n❌ Failed to start Sim containers" -ForegroundColor Red
    Write-Host "Please check Docker logs for more information." -ForegroundColor Yellow
}

Write-Host "`nPress Enter to close this window..." -ForegroundColor Gray
Read-Host
