@echo off
setlocal
cd /d "%~dp0"
set /p SERVER_IP=Enter server IP (use 127.0.0.1 for this PC): 
set /p CLIENT_COUNT=Number of concurrent clients (e.g. 25): 
where py >nul 2>nul
if %errorlevel%==0 (
    py load_test.py --host "%SERVER_IP%" --port 5050 --clients %CLIENT_COUNT% --pings 2
) else (
    python load_test.py --host "%SERVER_IP%" --port 5050 --clients %CLIENT_COUNT% --pings 2
)
pause
