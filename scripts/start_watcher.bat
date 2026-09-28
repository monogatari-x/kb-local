@echo off
REM kb-local watcher launcher (called by Task Scheduler)
REM Log: %USERPROFILE%\.kb\watcher.log
REM To disable this local watcher (after switching to the central instance),
REM create file %USERPROFILE%\.kb\DISABLE_LOCAL_KB and this script exits silently.
REM NOTE: keep this file ASCII-only. cmd.exe parses it with the ANSI codepage;
REM UTF-8 Chinese comments break the if-block parsing (verified 2026-09-28).

if exist "%USERPROFILE%\.kb\DISABLE_LOCAL_KB" (
    echo [%date% %time%] DISABLE_LOCAL_KB marker present, local watcher disabled >> "%USERPROFILE%\.kb\watcher.log"
    exit /b 0
)

setlocal
set HF_HUB_OFFLINE=1
set PYTHONUNBUFFERED=1
set LOG_DIR=%USERPROFILE%\.kb

REM Clear proxies: SOCKS proxy makes qdrant_client raise ImportError on httpx client build.
set ALL_PROXY=
set all_proxy=
set HTTP_PROXY=
set http_proxy=
set HTTPS_PROXY=
set https_proxy=

REM Locate project root relative to this script (drive letter changed once, never hardcode).
cd /d "%~dp0.."
set KB_PROJECT_DIR=%CD%

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Rotate previous log on each start.
if exist "%LOG_DIR%\watcher.log" move /Y "%LOG_DIR%\watcher.log" "%LOG_DIR%\watcher.prev.log" >nul

REM uv lives in the user dir; Task Scheduler does not include it in PATH.
set PATH=%USERPROFILE%\.local\bin;%PATH%

echo [%date% %time%] starting kb watch (dir=%KB_PROJECT_DIR%) >> "%LOG_DIR%\watcher.log"
uv run kb watch start >> "%LOG_DIR%\watcher.log" 2>&1
set EXIT_CODE=%errorlevel%
echo [%date% %time%] watcher exited with code %EXIT_CODE% >> "%LOG_DIR%\watcher.log"

REM Propagate exit code so Task Scheduler failure-restart can trigger.
exit /b %EXIT_CODE%
