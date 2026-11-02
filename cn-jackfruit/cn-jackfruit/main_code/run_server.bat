@echo off
cd /d "%~dp0"
python server.py --host 0.0.0.0 --port 5050 --duration 180 --max-connections 100
pause
