@echo off
REM kb-local Docker + Qdrant 启动脚本(由任务计划程序调用)
REM 日志:%USERPROFILE%\.kb\docker.log

setlocal
set LOG_DIR=%USERPROFILE%\.kb

REM 用脚本自身位置定位项目根:项目曾从 C: 迁到 D:,写死盘符会失效
cd /d "%~dp0.."
set KB_PROJECT_DIR=%CD%

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 等待 Docker Desktop 就绪(最多 120 秒)
set WAITED=0
:wait_docker
docker info >nul 2>&1
if %errorlevel%==0 goto docker_ready
set /a WAITED+=5
if %WAITED% geq 120 (
    echo [%date% %time%] Docker Desktop did not start within 120s, aborting >> "%LOG_DIR%\docker.log"
    exit /b 1
)
timeout /t 5 /nobreak >nul
goto wait_docker

:docker_ready
echo [%date% %time%] Docker Desktop is ready >> "%LOG_DIR%\docker.log"

docker compose up -d >> "%LOG_DIR%\docker.log" 2>&1
echo [%date% %time%] docker compose up -d exited with code %errorlevel% >> "%LOG_DIR%\docker.log"
