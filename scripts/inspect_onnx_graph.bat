@echo off
setlocal
cd /d "%~dp0.."
title Locomotive Analyzer - ONNX Graph Inspection

set "BASE_PY=.venv\Scripts\python.exe"
set "DIAG_PY=diagnostics\.venv\Scripts\python.exe"

if not exist "%BASE_PY%" (
  echo [ERROR] Main Python environment not found.
  echo Run the project starter once to prepare the environment.
  pause
  exit /b 1
)

if not exist "%DIAG_PY%" (
  echo Creating an isolated diagnostics environment...
  "%BASE_PY%" -m venv diagnostics\.venv
  if errorlevel 1 (
    echo [ERROR] Could not create the diagnostics environment.
    pause
    exit /b 1
  )
)

"%DIAG_PY%" -c "import onnx" >nul 2>&1
if errorlevel 1 (
  echo Installing the ONNX parser into the isolated diagnostics environment...
  "%DIAG_PY%" -m pip install --disable-pip-version-check "onnx>=1.17,<2"
  if errorlevel 1 (
    echo [ERROR] Could not install ONNX parser. Check internet and try again.
    pause
    exit /b 1
  )
)

"%DIAG_PY%" -u "scripts\inspect_onnx_graph.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo Graph inspection completed.
) else (
  echo Graph inspection exited with code %RESULT%.
)
pause
exit /b %RESULT%
