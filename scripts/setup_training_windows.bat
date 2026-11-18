@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Python 3.11 64-bit was not found.
    echo Install Python 3.11 x64 and enable the Python Launcher, then retry.
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
pip install -r requirements-train.txt
if errorlevel 1 exit /b 1
if not exist training\data mkdir training\data
if not exist public\models mkdir public\models
echo Copy LocomotivDataSet.xlsx into training\data\
echo Then run scripts\run_training_pipeline_windows.bat
endlocal
