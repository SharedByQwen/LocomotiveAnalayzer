@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (echo Run scripts\setup_backend_windows.bat first. & exit /b 1)
start "Locomotive Backend API" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
call npm run dev
endlocal
