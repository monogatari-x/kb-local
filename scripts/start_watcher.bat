@echo off
REM kb-local watcher 启动脚本(由任务计划程序调用)
REM 日志:%USERPROFILE%\.kb\watcher.log
REM 停用本机实例(切到中心实例时):创建 %USERPROFILE%\.kb\DISABLE_LOCAL_KB 即静默退出

if exist "%USERPROFILE%\.kb\DISABLE_LOCAL_KB" (
    echo [%date% %time%] DISABLE_LOCAL_KB marker present, local watcher disabled >> "%USERPROFILE%\.kb\watcher.log"
    exit /b 0
)

setlocal
set HF_HUB_OFFLINE=1
set PYTHONUNBUFFERED=1
set LOG_DIR=%USERPROFILE%\.kb

REM 清代理:SOCKS 代理会让 qdrant_client 构造 httpx 客户端时 ImportError,管线建不起来
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
if exist "%LOG_DIR%\watcher.log" move /Y "%LOG_DIR%\watcher.log" "%LOG_DIR%\watcher.prev.log" >nul

REM uv 在用户目录,Task Scheduler 默认不带这个 PATH
set PATH=%USERPROFILE%\.local\bin;%PATH%

echo [%date% %time%] starting kb watch (dir=%KB_PROJECT_DIR%) >> "%LOG_DIR%\watcher.log"
uv run kb watch start >> "%LOG_DIR%\watcher.log" 2>&1
set EXIT_CODE=%errorlevel%
echo [%date% %time%] watcher exited with code %EXIT_CODE% >> "%LOG_DIR%\watcher.log"

REM 把退出码透传给任务计划程序,否则"失败自动重启"永不触发
exit /b %EXIT_CODE%
