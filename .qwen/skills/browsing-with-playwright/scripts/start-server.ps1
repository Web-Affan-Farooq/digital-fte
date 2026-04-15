#!/usr/bin/env pwsh
# Start Playwright MCP server for browser-use skill
# Usage: .\start-server.ps1 [[port]]

param(
    [int]$port = 8808
)

$pidFile = "$env:TEMP\playwright-mcp-$port.pid"

# Check if already running
if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile
    try {
        $process = Get-Process -Id $existingPid -ErrorAction Stop
        Write-Host "Playwright MCP already running on port $port (PID: $existingPid)"
        exit 0
    } catch {
        # Process doesn't exist, remove stale PID file
        Remove-Item $pidFile -Force
    }
}

# Start server
$process = Start-Process -NoNewWindow -PassThru -FilePath "npx" -ArgumentList "@playwright/mcp@latest --port $port --shared-browser-context"

# Save PID
$process.Id | Out-File -FilePath $pidFile

# Wait a moment to verify it's running
Start-Sleep -Seconds 2

$runningProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
if ($runningProcess) {
    Write-Host "Playwright MCP started on port $port (PID: $($process.Id))"
} else {
    Write-Host "Failed to start Playwright MCP"
    Remove-Item $pidFile -Force
    exit 1
}