@echo off
REM kb-local MCP HTTP server 启动脚本(由任务计划程序调用)
REM 日志:%USERPROFILE%\.kb\mcp_http.log
REM 端口 8765,仅监听 127.0.0.1;Claude Code 侧配 type=http 共用这一个常驻进程

setlocal
set KB_MCP_TRANSPORT=http
set KB_MCP_PORT=8765
set HF_HUB_OFFLINE=1
set PYTHONUNBUFFERED=1
set LOG_DIR=%USERPROFILE%\.kb

REM 清代理:SOCKS 代理会让 qdrant_client 构造 httpx 客户端时 ImportError,检索管线建不起来
set ALL_PROXY=
set all_proxy=
set HTTP_PROXY=
set http_proxy=
set HTTPS_PROXY=
set https_proxy=

REM 用脚本自身位置定位项目根:项目曾从 C: 迁到 D:,写死盘符会失效
cd /d "%~dp0.."
set KB_PROJECT_DIR=%CD%

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 每次启动轮转一份上次日志
if exist "%LOG_DIR%\mcp_http.log" move /Y "%LOG_DIR%\mcp_http.log" "%LOG_DIR%\mcp_http.prev.log" >nul

echo [%date% %time%] starting kb_mcp (transport=%KB_MCP_TRANSPORT% port=%KB_MCP_PORT%) >> "%LOG_DIR%\mcp_http.log"

:serve
REM 自愈循环:进程挂掉就 5 秒后重起(启动文件夹方式没有任务计划的"失败重启",故在此实现)
"%KB_PROJECT_DIR%\.venv\Scripts\python.exe" -m kb_mcp >> "%LOG_DIR%\mcp_http.log" 2>&1
set EXIT_CODE=%errorlevel%
echo [%date% %time%] kb_mcp exited with code %EXIT_CODE%, restarting in 5s >> "%LOG_DIR%\mcp_http.log"
timeout /t 5 /nobreak >nul
goto serve
