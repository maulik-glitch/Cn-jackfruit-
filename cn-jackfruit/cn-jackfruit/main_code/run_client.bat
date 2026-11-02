@echo off
cd /d "%~dp0"
set /p SERVER_IP=Enter server IP (use 127.0.0.1 for this PC): 
set /p STUDENT_NAME=Enter student name: 
python client.py --host %SERVER_IP% --port 5050 --name "%STUDENT_NAME%"
pause
