@echo off
:: Sim Startup Batch File
:: This runs the PowerShell script with appropriate permissions

echo Starting Sim AI Agent Workflow Platform...
echo Please wait while Docker Desktop starts...

:: Wait 30 seconds for Docker Desktop to initialize after Windows startup
timeout /t 30 /nobreak > nul

:: Run the PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\LX\Documents\Project California\start-sim.ps1"

:: Keep window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo.
    echo An error occurred while starting Sim.
    pause
)
