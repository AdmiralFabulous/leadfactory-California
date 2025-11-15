# Sim Control Script - Start/Stop/Status

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status"
)

$simPath = "C:\Users\LX\Documents\Project California\sim"
Set-Location $simPath

function Start-Sim {
    Write-Host "Starting Sim..." -ForegroundColor Yellow
    $env:POSTGRES_PORT = "5433"
    docker compose -f docker-compose.prod.yml up -d
    Start-Sleep -Seconds 3
    Get-SimStatus
}

function Stop-Sim {
    Write-Host "Stopping Sim..." -ForegroundColor Yellow
    docker compose -f docker-compose.prod.yml down
    Write-Host "✅ Sim stopped" -ForegroundColor Green
}

function Restart-Sim {
    Stop-Sim
    Start-Sleep -Seconds 2
    Start-Sim
}

function Get-SimStatus {
    Write-Host "`nSim Container Status:" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Cyan
    
    $containers = @(docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}" | Where-Object { $_ -match "sim-" })
    
    if ($containers.Count -gt 0) {
        $containers | ForEach-Object {
            $parts = $_.Split('|')
            $name = $parts[0]
            $status = $parts[1]
            $ports = $parts[2]
            
            $statusColor = if ($status -match "healthy|Up") { "Green" } else { "Yellow" }
            Write-Host "  $name" -NoNewline
            Write-Host " - $status" -ForegroundColor $statusColor
            
            if ($ports) {
                $portInfo = $ports -replace '0.0.0.0:', 'localhost:' -replace '\[::]:[\d]+,\s*', ''
                Write-Host "    Ports: $portInfo" -ForegroundColor Gray
            }
        }
        
        Write-Host "`n🚀 Sim URLs:" -ForegroundColor Green
        Write-Host "  Main App: http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  Realtime: http://localhost:3002" -ForegroundColor Cyan
        Write-Host "  Database: localhost:5433" -ForegroundColor Cyan
    } else {
        Write-Host "  No Sim containers are running" -ForegroundColor Red
    }
}

# Execute the requested action
switch ($Action) {
    "start" { Start-Sim }
    "stop" { Stop-Sim }
    "restart" { Restart-Sim }
    "status" { Get-SimStatus }
}

Write-Host "`nPress Enter to exit..." -ForegroundColor Gray
Read-Host
