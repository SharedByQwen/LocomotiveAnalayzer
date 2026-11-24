@echo off
setlocal
cd /d "%~dp0.."
title Locomotive Analyzer - Model Diagnostics

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Python environment not found. Run scripts\start_windows.bat once first.
  pause
  exit /b 1
)

echo Running bounded ONNX load diagnostics.
echo Each ONNX session test is limited to 40 seconds.
echo Expected total time: about 2-3 minutes, not 15 minutes.
echo.
".venv\Scripts\python.exe" -u "scripts\diagnose_model_load.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo Diagnostics completed.
  echo Log: diagnostics\model_load_diagnostics.log
) else (
  echo Diagnostics failed with exit code %RESULT%.
)
pause
exit /b %RESULT%
