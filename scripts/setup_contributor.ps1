# kb-local contributor setup (Windows).
# Purpose: auto-archive this machine's project docs/ to the company server every hour.
# Usage (from the cloned kb-local repo root):
#   powershell -ExecutionPolicy Bypass -File scripts\setup_contributor.ps1 -Author pingtao.cao
# Prerequisites (script will remind):
#   - kb-local repo cloned locally
#   - Server account on 192.168.0.10 created by ops, added to group `rag`,
#     and your public key appended to its authorized_keys
# NOTE: keep this file ASCII-only (PowerShell 5.1 reads BOM-less files as ANSI).

param(
    [Parameter(Mandatory = $true)][string]$Author,   # zentao account, e.g. pingtao.cao
    [string]$SshUser = "",                           # server account, defaults to Author
    [string]$ProjectRoot = "D:\Glow\Projects"        # local projects root
)
$ErrorActionPreference = "Stop"
if (-not $SshUser) { $SshUser = $Author }
$kbDir = Split-Path -Parent $PSScriptRoot
$kbHome = Join-Path $env:USERPROFILE ".kb"

Write-Host "== kb-local contributor setup =="
Write-Host "repo: $kbDir"
Write-Host "author: $Author  server user: $SshUser"
Write-Host "projects root: $ProjectRoot"

# 1. uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[1/6] installing uv ..."
    curl.exe -LsSf https://astral.sh/uv/install.ps1 -o "$env:TEMP\uv_install.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\uv_install.ps1"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
} else { Write-Host "[1/6] uv present" }

# 2. Python deps (no AI model download needed for contributors)
Write-Host "[2/6] installing python deps (3-5 min first time) ..."
Push-Location $kbDir
uv sync --python 3.12
Pop-Location

# 3. Write ~/.kb/config.yaml (backup account + author identity)
Write-Host "[3/6] writing $kbHome\config.yaml ..."
New-Item -ItemType Directory -Force -Path $kbHome | Out-Null
$cfg = @"
author: $Author
backup:
  server: 192.168.0.10
  user: $SshUser
  key: ~/.ssh/id_rsa_2048
  remote_root: /data/RAG/bak
"@
Set-Content -Encoding ascii -Path (Join-Path $kbHome "config.yaml") -Value $cfg

# 4. ssh key (generate if missing) + ops request file
$keyPath = Join-Path $env:USERPROFILE ".ssh\id_rsa_2048"
if (-not (Test-Path $keyPath)) {
    Write-Host "[4/6] generating ssh key ..."
    ssh-keygen -t rsa -b 2048 -f $keyPath -N '""' -q
}
$pubkey = (Get-Content "$keyPath.pub" -Raw).Trim()
$request = @"
author=$Author
ssh_user=$SshUser
pubkey=$pubkey
"@
$reqFile = Join-Path ([Environment]::GetFolderPath("Desktop")) "kb-provision-request.txt"
Set-Content -Encoding ascii -Path $reqFile -Value $request
Write-Host "[4/6] request file written: $reqFile"
Write-Host "     SEND THIS FILE to the kb-local admin (cao). Server-side provisioning"
Write-Host "     (rag group + pubkey + central watch) is done by the admin in one command."

# 5. watch dir (all <project>/docs/ under ProjectRoot)
Write-Host "[5/6] configuring watch dir ..."
Push-Location $kbDir
uv run --python 3.12 kb watch add $ProjectRoot --project glow --strategy first_subdir `
    --include "*/docs/*" --exclude "**/node_modules/**" --exclude "**/vendor/**" `
    --exclude "**/.venv/**" --exclude "**/.git/**" --author $Author
Pop-Location

# 6. hourly backup task (runs as the current user - NO admin rights needed)
Write-Host "[6/6] registering hourly backup task ..."
$proc = Start-Process schtasks -ArgumentList '/create','/tn','kb-local-backup',
    '/tr',"'$kbDir\scripts\backup_scheduled.bat'",'/sc','hourly','/mo','1','/f' `
    -NoNewWindow -PassThru -Wait
if ($proc.ExitCode -ne 0) {
    Write-Host "[WARN] schtasks exit $($proc.ExitCode) - run manually if this failed:"
    Write-Host "  schtasks /create /tn kb-local-backup /tr `"$kbDir\scripts\backup_scheduled.bat`" /sc hourly /mo 1 /f"
}

Write-Host ""
Write-Host "== done. verify =="
Write-Host "1. send $reqFile to the admin, wait for the 'provisioned' reply"
Write-Host "2. then test once:  cd $kbDir ; uv run python scripts\backup.py --dry-run"
Write-Host "3. hourly backup runs automatically; put docs into $ProjectRoot\<project>\docs\"
Write-Host "4. search access (token from admin): add one MCP config to Claude Code / Codex."
