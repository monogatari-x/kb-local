@echo off
REM kb-local MCP HTTP server launcher (called by Task Scheduler)
REM Log: %USERPROFILE%\.kb\mcp_http.log
REM Port 8765, loopback only; shared by all local Claude Code sessions.
REM To disable this local instance (after switching to the central one),
REM create file %USERPROFILE%\.kb\DISABLE_LOCAL_KB and this script exits silently.
REM NOTE: keep this file ASCII-only. cmd.exe parses it with the ANSI codepage;
REM UTF-8 Chinese comments break the if-block parsing (verified 2026-09-28).

if exist "%USERPROFILE%\.kb\DISABLE_LOCAL_KB" (
    echo [%date% %time%] DISABLE_LOCAL_KB marker present, local instance disabled >> "%USERPROFILE%\.kb\mcp_http.log"
    exit /b 0
)

setlocal
set KB_MCP_TRANSPORT=http
set KB_MCP_PORT=8765
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
if exist "%LOG_DIR%\mcp_http.log" move /Y "%LOG_DIR%\mcp_http.log" "%LOG_DIR%\mcp_http.prev.log" >nul

echo [%date% %time%] starting kb_mcp (transport=%KB_MCP_TRANSPORT% port=%KB_MCP_PORT%) >> "%LOG_DIR%\mcp_http.log"

REM Wait for Qdrant (max 180s): if prewarm runs before Qdrant is up, first search
REM would load the model in a worker thread, which has a GIL-deadlock history.
set WAITED=0
:wait_qdrant
curl -s --noproxy "*" -o nul http://127.0.0.1:6333
if %errorlevel%==0 goto qdrant_ready
set /a WAITED+=5
if %WAITED% geq 180 (
    echo [%date% %time%] Qdrant not ready within 180s, starting anyway >> "%LOG_DIR%\mcp_http.log"
    goto serve
)
timeout /t 5 /nobreak >nul
goto wait_qdrant

:qdrant_ready
echo [%date% %time%] Qdrant is ready (waited %WAITED%s) >> "%LOG_DIR%\mcp_http.log"

:serve
REM Self-heal loop: restart after crash, and re-wait for Qdrant (crash cause may be Qdrant down).
"%KB_PROJECT_DIR%\.venv\Scripts\python.exe" -m kb_mcp >> "%LOG_DIR%\mcp_http.log" 2>&1
set EXIT_CODE=%errorlevel%
echo [%date% %time%] kb_mcp exited with code %EXIT_CODE%, restarting in 5s >> "%LOG_DIR%\mcp_http.log"
timeout /t 5 /nobreak >nul
goto wait_qdrant
