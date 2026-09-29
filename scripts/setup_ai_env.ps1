# Configure a NEW Windows user's Claude Code: relay settings + kb-local search MCP.
# Run BY THE NEW USER on their machine (writes into their own profile - no admin needed).
#
# Admin prepares a folder with two files, then sends the folder to the user:
#   claude-settings.json   - the relay settings.json (from admin's ~/.claude/settings.json)
#   central_token.txt      - the kb-local search token
# Both files must sit NEXT TO this script when it runs.
#
# Usage (new user, from the received folder):
#   powershell -ExecutionPolicy Bypass -File setup_ai_env.ps1
# NOTE: ASCII-only for PS 5.1.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$settingsSrc = Join-Path $here "claude-settings.json"
$tokenSrc = Join-Path $here "central_token.txt"
foreach ($f in @($settingsSrc, $tokenSrc)) {
    if (-not (Test-Path $f)) {
        Write-Host "[FAIL] missing $f - ask the admin for the complete folder."; exit 1
    }
}

# 1. relay settings (ANTHROPIC_BASE_URL / token / model mapping)
$claudeDir = Join-Path $env:USERPROFILE ".claude"
New-Item -ItemType Directory -Force -Path $claudeDir | Out-Null
Copy-Item $settingsSrc (Join-Path $claudeDir "settings.json") -Force
Write-Host "[1/2] relay settings installed"

# 2. kb-local MCP into .claude.json
$token = (Get-Content $tokenSrc -Raw).Trim()
$cfgPath = Join-Path $env:USERPROFILE ".claude.json"
if (Test-Path $cfgPath) {
    $json = Get-Content $cfgPath -Raw | ConvertFrom-Json
} else {
    $json = New-Object PSObject
}
if (-not $json.PSObject.Properties["mcpServers"]) {
    $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue (New-Object PSObject)
}
$entry = New-Object PSObject -Property @{ type = "http"; url = "http://192.168.0.10:8766/mcp" }
$entry | Add-Member -NotePropertyName headers -NotePropertyValue (
    New-Object PSObject -Property @{ Authorization = "Bearer $token" }
)
if ($json.mcpServers.PSObject.Properties["kb-local"]) {
    $json.mcpServers.PSObject.Properties.Remove("kb-local")
}
$json.mcpServers | Add-Member -NotePropertyName kb-local -NotePropertyValue $entry -Force
$json | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $cfgPath
Write-Host "[2/2] kb-local MCP added"
Write-Host "done - open a NEW PowerShell window and run: claude"
Write-Host "then ask: 'Search kb-local for <anything>' (用 kb_search 搜索任意内容)"
