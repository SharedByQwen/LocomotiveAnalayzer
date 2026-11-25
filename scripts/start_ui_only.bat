@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title Locomotive Analyzer - UI Only

set "VENV_PY=.venv\Scripts\python.exe"
set "BACKEND_PID=.backend-ui-only.pid"

echo.
echo ========================================
echo   Locomotive Analyzer - UI Only Mode
echo ========================================
echo.
echo Model loading is intentionally disabled for this run.
echo The API and UI will start even when the ONNX model is unavailable.
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js is required.
  pause
  exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is required.
  pause
  exit /b 1
)

if not exist "%VENV_PY%" (
  py -3.11 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create Python virtual environment.
    pause
    exit /b 1
  )
)

powershell -NoProfile -Command "if(!(Test-Path '.venv/.requirements-installed') -or (Get-Item 'backend/requirements.txt').LastWriteTimeUtc -gt (Get-Item '.venv/.requirements-installed').LastWriteTimeUtc){exit 1}else{exit 0}"
if errorlevel 1 (
  call "%VENV_PY%" -m pip install --disable-pip-version-check -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] Python dependency installation failed.
    pause
    exit /b 1
  )
  type nul > ".venv\.requirements-installed"
)

if not exist "node_modules" (
  call npm install
  if errorlevel 1 (
    echo [ERROR] Frontend dependency installation failed.
    pause
    exit /b 1
  )
) else if not exist "node_modules\.package-lock.json" (
  call npm install
  if errorlevel 1 exit /b 1
) else (
  powershell -NoProfile -Command "if((Get-Item package-lock.json).LastWriteTime -gt (Get-Item node_modules/.package-lock.json).LastWriteTime){exit 1}else{exit 0}"
  if errorlevel 1 (
    call npm install
    if errorlevel 1 (
      echo [ERROR] Frontend dependency update failed.
      pause
      exit /b 1
    )
  )
)

echo [1/2] Starting backend without loading ONNX model...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pidFile='.backend-ui-only.pid'; if(Test-Path $pidFile){$old=Get-Content $pidFile -ErrorAction SilentlyContinue; if($old){$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$old) -ErrorAction SilentlyContinue; if($proc -and $proc.CommandLine -like '*uvicorn backend.app:app*'){Stop-Process -Id ([int]$old) -Force; Start-Sleep -Seconds 1}}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}; $env:LOCOMOTIVE_SKIP_MODEL_LOAD='1'; $p=Start-Process -FilePath '%CD%\.venv\Scripts\python.exe' -ArgumentList '-u','-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%CD%' -WindowStyle Minimized -RedirectStandardOutput '%CD%\backend\backend.stdout.log' -RedirectStandardError '%CD%\backend\backend.stderr.log' -PassThru; Set-Content -Path $pidFile -Value $p.Id"
if errorlevel 1 (
  echo [ERROR] Could not start backend.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ready=$false; for($i=0;$i -lt 30;$i++){try{$h=Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if($h.status -eq 'ok'){$ready=$true;break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ready){Write-Host 'Backend did not become ready. Logs:'; Get-Content 'backend/backend.stdout.log','backend/backend.stderr.log' -Tail 60; exit 1}"
if errorlevel 1 (
  echo [ERROR] Backend health check failed.
  pause
  exit /b 1
)

echo [2/2] Starting frontend...
echo.
echo Backend: http://127.0.0.1:8000
echo UI:      http://127.0.0.1:5173
echo Model:   intentionally disabled for this session
echo.
call npm run dev
endlocal
