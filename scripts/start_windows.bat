@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title Locomotive Analyzer

set "MODEL_ZIP=backend\models\model_bundle.zip"
set "VENV_PY=.venv\Scripts\python.exe"
set "BACKEND_PID=.backend.pid"

echo.
echo ========================================
echo        Locomotive Analyzer
echo ========================================
echo.

if not exist "%MODEL_ZIP%" (
  echo [ERROR] Model ZIP not found:
  echo %CD%\%MODEL_ZIP%
  echo.
  echo Put model_bundle.zip in backend\models and run again.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js LTS is required.
  pause
  exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.11 or newer is required.
  pause
  exit /b 1
)

echo [1/4] Checking Python environment...
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

echo [2/4] Checking frontend dependencies...
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

echo [3/4] Starting backend with the local model ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pidFile='.backend.pid'; if(Test-Path $pidFile){$old=Get-Content $pidFile -ErrorAction SilentlyContinue; if($old){$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$old) -ErrorAction SilentlyContinue; if($proc -and $proc.CommandLine -like '*uvicorn backend.app:app*'){Stop-Process -Id ([int]$old) -Force; Start-Sleep -Seconds 1}}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}; $p=Start-Process -FilePath '%CD%\.venv\Scripts\python.exe' -ArgumentList '-u','-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%CD%' -WindowStyle Minimized -RedirectStandardOutput '%CD%\backend\backend.stdout.log' -RedirectStandardError '%CD%\backend\backend.stderr.log' -PassThru; Set-Content -Path $pidFile -Value $p.Id"
if errorlevel 1 (
  echo [ERROR] Could not start backend.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ready=$false; $limit=900; for($i=0;$i -lt $limit;$i++){try{$s=Invoke-RestMethod 'http://127.0.0.1:8000/api/model/status' -TimeoutSec 2; if($s.loaded){$ready=$true; Write-Host ('[OK] Model ready: '+$s.algorithm); break}}catch{}; if((($i+1)%%30) -eq 0){Write-Host ('Waiting for model load... '+($i+1)+'/'+ $limit +' seconds')}; Start-Sleep -Seconds 1}; if(-not $ready){Write-Host 'Backend log:'; Get-Content 'backend/backend.stdout.log','backend/backend.stderr.log' -Tail 80; exit 1}"
if errorlevel 1 (
  echo [ERROR] Model could not be loaded. See backend\backend.stderr.log
  pause
  exit /b 1
)

echo [4/4] Starting frontend...
echo.
echo Open http://127.0.0.1:5173
echo Keep this window open while using the app.
echo.
call npm run dev
endlocal
