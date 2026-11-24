@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" verify_pc.py
if errorlevel 1 goto failed
echo Ready. Open run_pc.bat to start.
pause
exit /b 0
:failed
echo Installation or verification failed. Read the error above.
pause
exit /b 1
