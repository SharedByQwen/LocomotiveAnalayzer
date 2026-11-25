@echo off
setlocal
cd /d "%~dp0.."
title Locomotive Analyzer - ONNX Graph Inspection

if not exist "diagnostics\\diagnostic_model.onnx" (
  echo [ERROR] Extracted model not found.
  echo Run scripts\\diagnose_model_load.bat first.
  pause
  exit /b 1
)

if not exist ".venv\\Scripts\\python.exe" (
  echo [ERROR] Python environment not found.
  pause
  exit /b 1
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
