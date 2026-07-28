@echo off
REM kb-local watcher 启动脚本(由任务计划程序调用)
REM 日志:%USERPROFILE%\.kb\watcher.log

setlocal
set HF_HUB_OFFLINE=1
set PYTHONUNBUFFERED=1
set KB_PROJECT_DIR=C:\Glow\Projects\kb-local
set LOG_DIR=%USERPROFILE%\.kb

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 每次启动轮转一份上次日志
if exist "%LOG_DIR%\watcher.log" move /Y "%LOG_DIR%\watcher.log" "%LOG_DIR%\watcher.prev.log" >nul

REM uv 在用户目录,Task Scheduler 默认不带这个 PATH
set PATH=%USERPROFILE%\.local\bin;%PATH%

cd /d %KB_PROJECT_DIR%
echo [%date% %time%] starting kb watch >> "%LOG_DIR%\watcher.log"
uv run kb watch start >> "%LOG_DIR%\watcher.log" 2>&1
echo [%date% %time%] watcher exited with code %errorlevel% >> "%LOG_DIR%\watcher.log"
