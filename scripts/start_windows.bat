@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title Locomotive Analyzer - Setup and Run

echo.
echo ==========================================
echo       Locomotive Analyzer
echo       One-step setup and launch
echo ==========================================
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js is not installed.
  echo Install Node.js LTS from https://nodejs.org/ and run this file again.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher was not found.
  echo Install Python 3.11 or newer and enable the Python Launcher.
  pause
  exit /b 1
)

echo [1/5] Select the ZIP model exported from Google Colab...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Title='Select Locomotive Analyzer model ZIP'; $d.Filter='ZIP model bundle (*.zip)|*.zip'; $d.Multiselect=$false; if($d.ShowDialog() -eq 'OK'){Copy-Item -LiteralPath $d.FileName -Destination '%CD%\backend\models\model_bundle.zip' -Force; exit 0}else{exit 2}"
if errorlevel 1 (
  echo [ERROR] No ZIP was selected or the model could not be copied.
  pause
  exit /b 1
)
echo [OK] ZIP saved to backend\models\model_bundle.zip
echo.

echo [2/5] Preparing Python environment...
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create Python virtual environment.
    echo Python 3.11 or newer is required.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependencies installation failed.
  pause
  exit /b 1
)
echo.

echo [3/5] Installing frontend dependencies...
call npm install
if errorlevel 1 (
  echo [ERROR] npm install failed.
  pause
  exit /b 1
)
echo.

echo [4/5] Starting backend and checking model...
start "Locomotive Analyzer Backend" /min cmd /c ""%CD%\.venv\Scripts\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok=$false; for($i=0;$i -lt 30;$i++){try{$h=Invoke-RestMethod 'http://127.0.0.1:8000/api/model/status' -TimeoutSec 2; if($h.loaded){$ok=$true; Write-Host ('[OK] Model loaded: '+$h.algorithm+' / '+$h.model_version); break}}catch{}; Start-Sleep -Seconds 1}; if(-not $ok){Write-Host '[ERROR] Backend did not load the model in time.'; exit 1}"
if errorlevel 1 (
  echo [ERROR] Backend failed to start or load the ZIP model.
  echo Check the Backend window for details.
  pause
  exit /b 1
)
echo.

echo [5/5] Starting the application...
echo Open http://127.0.0.1:5173 in your browser.
echo Keep this window open while using the application.
echo.
call npm run dev
endlocal
