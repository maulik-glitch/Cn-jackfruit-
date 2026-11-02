@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 100
) else (
    python server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 100
)
pause
