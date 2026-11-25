@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Locomotive Analyzer

echo.
echo ==========================================
echo          LOCOMOTIVE ANALYZER
echo ==========================================
echo.

set "PY_LAUNCHER="
set "VENV_PY=%CD%\.venv\Scripts\python.exe"

where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 --version >nul 2>nul && set "PY_LAUNCHER=py -3.12"
  if not defined PY_LAUNCHER py -3.11 --version >nul 2>nul && set "PY_LAUNCHER=py -3.11"
  if not defined PY_LAUNCHER py -3 --version >nul 2>nul && set "PY_LAUNCHER=py -3"
)

if not defined PY_LAUNCHER (
  echo [SETUP] Python was not found. Trying to install Python 3.12...
  where winget >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Install Python 3.12 x64 and run START.bat again.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
  )
  winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [ERROR] Automatic Python installation failed.
    pause
    exit /b 1
  )
  set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
  where py >nul 2>nul
  if not errorlevel 1 py -3.12 --version >nul 2>nul && set "PY_LAUNCHER=py -3.12"
  if not defined PY_LAUNCHER (
    echo [ERROR] Python was installed but the launcher could not detect it.
    pause
    exit /b 1
  )
)

where node >nul 2>nul
if errorlevel 1 (
  echo [SETUP] Node.js LTS was not found. Trying to install it...
  where winget >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Install Node.js LTS and run START.bat again.
    echo Download: https://nodejs.org/
    pause
    exit /b 1
  )
  winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [ERROR] Automatic Node.js installation failed.
    pause
    exit /b 1
  )
  set "PATH=%PATH%;%ProgramFiles%\nodejs;%LOCALAPPDATA%\Programs\nodejs"
  where node >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Node.js was installed but could not be detected in this session.
    echo Close this window, open START.bat again.
    pause
    exit /b 1
  )
)

echo [1/6] Preparing Python environment...
if not exist "%VENV_PY%" (
  call %PY_LAUNCHER% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the Python virtual environment.
    pause
    exit /b 1
  )
)
"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
  "%VENV_PY%" -m ensurepip --upgrade
  if errorlevel 1 (
    echo [ERROR] Python pip is unavailable.
    pause
    exit /b 1
  )
)
powershell -NoProfile -Command "if(!(Test-Path '.venv/.requirements-installed') -or (Get-Item 'backend/requirements.txt').LastWriteTimeUtc -gt (Get-Item '.venv/.requirements-installed').LastWriteTimeUtc){exit 1}else{exit 0}"
if errorlevel 1 (
  "%VENV_PY%" -m pip install --disable-pip-version-check -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] Python dependency installation failed. Check your internet connection.
    pause
    exit /b 1
  )
  type nul > ".venv\.requirements-installed"
)

echo [2/6] Preparing frontend dependencies...
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
  powershell -NoProfile -Command "if((Get-Item package.json).LastWriteTimeUtc -gt (Get-Item node_modules/.package-lock.json).LastWriteTimeUtc){exit 1}else{exit 0}"
  if errorlevel 1 (
    call npm install
    if errorlevel 1 (
      echo [ERROR] Frontend dependency update failed.
      pause
      exit /b 1
    )
  )
)

echo [3/6] Running frontend tests...
call npm test
if errorlevel 1 (
  echo [ERROR] Frontend tests failed.
  pause
  exit /b 1
)
call npm run build
if errorlevel 1 (
  echo [ERROR] Frontend production build failed.
  pause
  exit /b 1
)
"%VENV_PY%" -m compileall -q backend
if errorlevel 1 (
  echo [ERROR] Backend Python syntax check failed.
  pause
  exit /b 1
)

echo [4/6] Starting backend (model loads in background)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pidFiles=@('.backend.pid','.backend-ui-only.pid'); foreach($pidFile in $pidFiles){if(Test-Path $pidFile){$old=Get-Content $pidFile -ErrorAction SilentlyContinue; if($old){$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$old) -ErrorAction SilentlyContinue; if($proc -and $proc.CommandLine -like '*uvicorn backend.app:app*'){Stop-Process -Id ([int]$old) -Force; Start-Sleep -Seconds 1}}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}}; $p=Start-Process -FilePath '%CD%\.venv\Scripts\python.exe' -ArgumentList '-u','-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%CD%' -WindowStyle Minimized -RedirectStandardOutput '%CD%\backend\backend.stdout.log' -RedirectStandardError '%CD%\backend\backend.stderr.log' -PassThru; Set-Content -Path $pidFile -Value $p.Id"
if errorlevel 1 (
  echo [ERROR] Could not start backend.
  pause
  exit /b 1
)

echo [5/6] Waiting for backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ready=$false; for($i=0;$i -lt 30;$i++){try{$h=Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2; if($h.status -eq 'ok'){$ready=$true;break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ready){Write-Host 'Backend logs:'; Get-Content 'backend/backend.stdout.log','backend/backend.stderr.log' -Tail 60; exit 1}"
if errorlevel 1 (
  echo [ERROR] Backend did not become ready. Check backend\backend.stderr.log
  pause
  exit /b 1
)

echo [6/6] Starting frontend...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pidFile='.frontend.pid'; if(Test-Path $pidFile){$old=Get-Content $pidFile -ErrorAction SilentlyContinue; if($old){$proc=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$old) -ErrorAction SilentlyContinue; if($proc -and $proc.CommandLine -like '*npm run dev*'){Stop-Process -Id ([int]$old) -Force}}; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue}; $p=Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev' -WorkingDirectory '%CD%' -WindowStyle Minimized -RedirectStandardOutput '%CD%\\frontend.stdout.log' -RedirectStandardError '%CD%\\frontend.stderr.log' -PassThru; Set-Content -Path $pidFile -Value $p.Id"
if errorlevel 1 (
  echo [ERROR] Could not start frontend.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ready=$false; for($i=0;$i -lt 30;$i++){try{$r=Invoke-WebRequest 'http://127.0.0.1:5173' -TimeoutSec 2; if($r.StatusCode -eq 200){$ready=$true;break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ready){Write-Host 'Frontend logs:'; Get-Content 'frontend.stdout.log','frontend.stderr.log' -Tail 60; exit 1}"
if errorlevel 1 (
  echo [ERROR] Frontend did not become ready.
  pause
  exit /b 1
)

echo.
echo Backend: http://127.0.0.1:8000
echo App:     http://127.0.0.1:5173
echo Model loading runs in the background. The UI remains available while it loads.
echo Keep this window open while using the app.
echo.
start "" http://127.0.0.1:5173
pause
exit /b 0
