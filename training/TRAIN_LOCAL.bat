@echo off
setlocal
cd /d "%~dp0.."

echo ==========================================
echo   Locomotive Analyzer - Local Trainer
echo ==========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating project virtual environment...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 py -3.11 -m venv .venv 2>nul
    if errorlevel 1 py -3 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python 3.11 or newer is required.
        pause
        exit /b 1
    )
)

echo [2/3] Installing training dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements-train.txt
if errorlevel 1 goto :failed

echo [3/3] Opening the local training application...
".venv\Scripts\python.exe" training\local_trainer.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo Training application could not start. Review the error above.
pause
exit /b 1
