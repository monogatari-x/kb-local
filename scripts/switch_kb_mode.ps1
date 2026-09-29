# Switch kb-local between CENTRAL (company network) and OFFLINE (local replica).
#   offline: start local MCP (port 8765, no token, loopback) + point Claude/Codex
#            MCP configs at 127.0.0.1:8765
#   online : stop local MCP + point configs back at the central server
# NOTE: ASCII-only for PS 5.1. Run from the kb-local repo (default RepoDir).

param(
    [Parameter(Mandatory = $true)][ValidateSet("offline", "online")][string]$Mode,
    [string]$RepoDir = "D:\Glow\Projects\kb-local",
    [string]$CentralUrl = "http://192.168.0.10:8766/mcp"
)
$ErrorActionPreference = "Stop"
$tokenFile = Join-Path $env:USERPROFILE ".kb\central_token.local"
if (-not (Test-Path $tokenFile)) { Write-Host "[FAIL] missing $tokenFile"; exit 1 }
$token = (Get-Content $tokenFile -Raw).Trim()

if ($Mode -eq "offline") {
    # already running?
    $running = Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -like "*kb_mcp*" }
    if (-not $running) {
        Write-Host "[1/2] starting local kb-local MCP on 127.0.0.1:8765 (model load ~90s) ..."
        $bat = Join-Path $RepoDir "scripts\start_mcp_http.bat"
        # bypass the DISABLE marker for this on-demand run (marker stays for autostart)
        $tmpMarker = "$env:USERPROFILE\.kb\DISABLE_LOCAL_KB"
        $hadMarker = Test-Path $tmpMarker
        if ($hadMarker) { Remove-Item $tmpMarker -Force }
        Start-Process cmd -ArgumentList '/c', "`"$bat`"" -WindowStyle Hidden
        if ($hadMarker) {
            Start-Sleep -Seconds 3
            New-Item -ItemType File -Path $tmpMarker -Force | Out-Null
        }
        Start-Sleep -Seconds 95
    } else {
        Write-Host "[1/2] local MCP already running"
    }

    Write-Host "[2/2] switching Claude Code + Codex MCP to local ..."
} else {
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -like "*kb_mcp*" } | ForEach-Object {
            taskkill /PID $_.ProcessId /T /F | Out-Null
        }
    Write-Host "[1/2] local MCP stopped"
    Write-Host "[2/2] switching Claude Code + Codex MCP to central ..."
}

# Claude Code (~/.claude.json)
$cfgPath = Join-Path $env:USERPROFILE ".claude.json"
$json = if (Test-Path $cfgPath) { Get-Content $cfgPath -Raw | ConvertFrom-Json } else { New-Object PSObject }
if (-not $json.PSObject.Properties["mcpServers"]) {
    $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue (New-Object PSObject)
}
$entry = if ($Mode -eq "offline") {
    New-Object PSObject -Property @{ type = "http"; url = "http://127.0.0.1:8765/mcp" }
} else {
    $e = New-Object PSObject -Property @{ type = "http"; url = $CentralUrl }
    $e | Add-Member -NotePropertyName headers -NotePropertyValue (
        New-Object PSObject -Property @{ Authorization = "Bearer $token" })
    $e
}
if ($json.mcpServers.PSObject.Properties["kb-local"]) {
    $json.mcpServers.PSObject.Properties.Remove("kb-local")
}
$json.mcpServers | Add-Member -NotePropertyName kb-local -NotePropertyValue $entry -Force
$json | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $cfgPath

# Codex (~/.codex/config.toml) - textual patch
$codexCfg = Join-Path $env:USERPROFILE ".codex\config.toml"
if (Test-Path $codexCfg) {
    $c = Get-Content $codexCfg -Raw
    if ($Mode -eq "offline") {
        $c = $c -replace 'url = "http://192\.168\.0\.10:8766/mcp"', 'url = "http://127.0.0.1:8765/mcp"'
    } else {
        $c = $c -replace 'url = "http://127\.0\.0\.1:8765/mcp"', "url = `"$CentralUrl`""
    }
    Set-Content -Encoding utf8 $codexCfg $c
}

Write-Host "done ($Mode). Restart your Claude Code / Codex session to take effect."
