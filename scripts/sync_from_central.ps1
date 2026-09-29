# Pull the personal kb-local replica from the central server and make it local-live.
# Daily at 18:10 via Task Scheduler (central exports at 17:40).
# Steps: scp personal db -> merge local watch_dirs -> swap local kb_meta.db
#        -> rebuild local Qdrant from the embedding cache (no model needed).
# Run from anywhere; assumes this repo is the admin's copy at a known path.
# NOTE: ASCII-only for PS 5.1.

param(
    [string]$Author = "pingtao.cao",
    [string]$Server = "192.168.0.10",
    [string]$SshUser = "caopingtao",
    [string]$RepoDir = "D:\Glow\Projects\kb-local"
)
$ErrorActionPreference = "Stop"
$kbHome = Join-Path $env:USERPROFILE ".kb"
$incoming = Join-Path $kbHome "sync_incoming.db"
$localDb = Join-Path $kbHome "kb_meta.db"

Write-Host "[1/4] pulling personal replica of $Author from $Server ..."
& "$env:systemroot\System32\OpenSSH\scp.exe" -i "$env:USERPROFILE\.ssh\id_rsa_2048" `
    -o BatchMode=yes -o StrictHostKeyChecking=accept-new `
    "${SshUser}@${Server}:/data/RAG/sync/kb-personal-$Author.db" "$incoming"
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] scp"; exit 1 }

Write-Host "[2/4] merging local watch_dirs + swapping local db ..."
$pyMerge = @'
import shutil, sqlite3, sys
incoming, local_db = sys.argv[1], sys.argv[2]
src = sqlite3.connect(incoming)
dst = sqlite3.connect(local_db)
watches = [tuple(r) for r in dst.execute(
    "SELECT path, project_name, project_strategy, recursive, file_types,"
    " include_patterns, exclude_patterns, created_at, author FROM watch_dirs"
).fetchall()]
src.executemany(
    "INSERT INTO watch_dirs(path, project_name, project_strategy, recursive,"
    " file_types, include_patterns, exclude_patterns, created_at, author)"
    " VALUES (?,?,?,?,?,?,?,?,?)", watches)
src.commit(); src.close(); dst.close()
shutil.copy2(local_db, local_db + ".bak")
shutil.move(incoming, local_db)
print(f"watch_dirs preserved: {len(watches)}")
'@
$pyMerge | & (Join-Path $RepoDir ".venv\Scripts\python.exe") - "$incoming" "$localDb"
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] db merge"; exit 1 }

Write-Host "[3/4] rebuilding local Qdrant from embedding cache ..."
Push-Location $RepoDir
$env:HF_HUB_OFFLINE = "1"
& (Join-Path $RepoDir ".venv\Scripts\python.exe") scripts\rebuild_qdrant_from_cache.py
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) { Write-Host "[FAIL] qdrant rebuild"; exit 1 }

Write-Host "[4/4] done. Offline replica is ready."
Write-Host "To use it offline: powershell -File scripts\switch_kb_mode.ps1 -Mode offline"
