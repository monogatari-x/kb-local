@echo off
rem Scheduled backup entry point for kb-local. Log: %USERPROFILE%\.kb\backup.log
cd /d "%~dp0.."
C:\Users\Lenovo\.local\bin\uv.exe run python scripts\backup.py >> "%USERPROFILE%\.kb\backup.log" 2>&1
