# Enable Docker Desktop to start automatically on Windows startup
Write-Host "Configuring Docker Desktop to start automatically..." -ForegroundColor Yellow

# Create registry entry for Docker Desktop startup
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

# Check if Docker Desktop exists
if (Test-Path $dockerPath) {
    # Add Docker Desktop to Windows startup
    Set-ItemProperty -Path $regPath -Name "Docker Desktop" -Value """$dockerPath""" -Type String
    Write-Host "✅ Docker Desktop configured to start automatically on Windows startup" -ForegroundColor Green
} else {
    Write-Host "❌ Docker Desktop not found at expected location" -ForegroundColor Red
}

# Verify the setting
$currentValue = Get-ItemProperty -Path $regPath -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($currentValue."Docker Desktop") {
    Write-Host "Current startup value: $($currentValue.'Docker Desktop')" -ForegroundColor Cyan
}
