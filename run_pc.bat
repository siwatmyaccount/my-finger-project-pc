@echo off
setlocal
cd /d "%~dp0"
set "PC_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%PC_PYTHON%" goto run
set "PC_PYTHON=%~dp0..\.venv-pc-v28\Scripts\python.exe"
if exist "%PC_PYTHON%" goto run
echo Please run install_pc.bat first.
pause
exit /b 1
:run
"%PC_PYTHON%" "%~dp0launch_pc.py" %*
set "PC_EXIT=%ERRORLEVEL%"
if not "%PC_EXIT%"=="0" (
    echo The program could not finish normally. Check data\v28\run.log.
    pause
)
exit /b %PC_EXIT%
