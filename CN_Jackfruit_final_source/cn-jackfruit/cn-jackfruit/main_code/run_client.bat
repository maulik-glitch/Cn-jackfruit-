@echo off
setlocal
cd /d "%~dp0"
set /p SERVER_IP=Enter server IP (use 127.0.0.1 for this PC): 
set /p STUDENT_NAME=Enter student name: 
where py >nul 2>nul
if %errorlevel%==0 (
    py client.py --host "%SERVER_IP%" --port 5050 --name "%STUDENT_NAME%"
) else (
    python client.py --host "%SERVER_IP%" --port 5050 --name "%STUDENT_NAME%"
)
pause
