#!/usr/bin/env pwsh
# Stop Playwright MCP server
# Usage: .\stop-server.ps1 [[port]]

param(
    [int]$port = 8808
)

$pidFile = "$env:TEMP\playwright-mcp-$port.pid"

function Stop-ProcessAndChildren {
    param([int]$pid)
    
    try {
        # Get the process
        $process = Get-Process -Id $pid -ErrorAction Stop
        
        # Try to close gracefully first
        Write-Host "Attempting to close Playwright MCP gracefully (PID: $pid)..."
        
        # Close the browser gracefully using MCP client if available
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $mcpClientPath = Join-Path $scriptDir "mcp-client.py"
        
        if (Test-Path $mcpClientPath) {
            try {
                python $mcpClientPath call -u "http://localhost:$port" -t browser_close -p '{}' 2>$null
            } catch {
                # Ignore errors from MCP client
            }
        }
        
        # Try to kill gracefully
        $process.CloseMainWindow() | Out-Null
        Start-Sleep -Milliseconds 500
        
        # Check if still running
        if (-not $process.HasExited) {
            Write-Host "Process still running, stopping forcefully..."
            $process.Kill()
            $process.WaitForExit(2000)
        }
        
        if ($process.HasExited) {
            Write-Host "✓ Playwright MCP stopped (was PID: $pid)"
            return $true
        } else {
            Write-Host "✗ Failed to stop process (PID: $pid)"
            return $false
        }
    } catch {
        Write-Host "Process with PID $pid not found"
        return $false
    }
}

# Check if we have a PID file
if (Test-Path $pidFile) {
    $pid = Get-Content $pidFile
    if ($pid -match '^\d+$') {
        Stop-ProcessAndChildren -pid $pid
    } else {
        Write-Host "Invalid PID in file: $pid"
    }
    Remove-Item $pidFile -Force
} else {
    # Try to find and kill by process name and arguments
    Write-Host "No PID file found, searching for Playwright MCP processes on port $port..."
    
    $processes = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*@playwright/mcp*" -and $_.CommandLine -like "*--port $port*"
    }
    
    if ($processes) {
        foreach ($process in $processes) {
            Write-Host "Found Playwright MCP process (PID: $($process.Id))"
            try {
                $process.CloseMainWindow() | Out-Null
                Start-Sleep -Milliseconds 500
                
                if (-not $process.HasExited) {
                    $process.Kill()
                    $process.WaitForExit(2000)
                }
                
                Write-Host "✓ Stopped Playwright MCP process (PID: $($process.Id))"
            } catch {
                Write-Host "✗ Failed to stop process (PID: $($process.Id)): $_"
            }
        }
    } else {
        # Try to find by port using netstat
        $netstat = netstat -ano | findstr ":$port" | findstr "LISTENING"
        if ($netstat) {
            $lines = $netstat -split "`r`n"
            foreach ($line in $lines) {
                if ($line -match '\s+(\d+)\s*$') {
                    $pid = $matches[1]
                    Write-Host "Found process listening on port $port (PID: $pid)"
                    Stop-ProcessAndChildren -pid $pid
                }
            }
        } else {
            Write-Host "Playwright MCP not running on port $port"
        }
    }
}