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

REM 等 Qdrant 就绪(最多 180 秒):prewarm 在 Qdrant 未起时会失败,之后首次检索
REM 只能在工作线程加载模型(有 GIL 死锁历史风险),故宁可在此等待
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
REM 自愈循环:进程挂掉就 5 秒后重起,并重走 Qdrant 等待(挂因可能就是 Qdrant 掉了)
"%KB_PROJECT_DIR%\.venv\Scripts\python.exe" -m kb_mcp >> "%LOG_DIR%\mcp_http.log" 2>&1
set EXIT_CODE=%errorlevel%
echo [%date% %time%] kb_mcp exited with code %EXIT_CODE%, restarting in 5s >> "%LOG_DIR%\mcp_http.log"
timeout /t 5 /nobreak >nul
goto wait_qdrant
