@echo off
rem Scheduled backup entry point for kb-local. Log: %USERPROFILE%\.kb\backup.log
rem Keep this file ASCII-only (cmd.exe parses it with the ANSI codepage).
cd /d "%~dp0.."
set PATH=%USERPROFILE%\.local\bin;%PATH%
uv run --python 3.12 python scripts\backup.py >> "%USERPROFILE%\.kb\backup.log" 2>&1
