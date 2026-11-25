@echo off
setlocal
cd /d "%~dp0.."
title Locomotive Analyzer - ONNX Graph Inspection

if not exist ".venv\\Scripts\\python.exe" (
  echo [ERROR] Python environment not found.
  pause
  exit /b 1
)

".venv\\Scripts\\python.exe" -c "import onnx" >nul 2>&1
if errorlevel 1 (
  echo Installing the ONNX graph inspection dependency...
  ".venv\\Scripts\\python.exe" -m pip install "onnx>=1.17,<2"
  if errorlevel 1 (
    echo [ERROR] Could not install ONNX parser. Check internet and try again.
    pause
    exit /b 1
  )
)

".venv\\Scripts\\python.exe" -u "scripts\\inspect_onnx_graph.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo Graph inspection completed.
) else (
  echo Graph inspection exited with code %RESULT%.
)
pause
exit /b %RESULT%
