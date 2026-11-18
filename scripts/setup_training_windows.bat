@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv py -3 -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
pip install -r requirements-train.txt
if errorlevel 1 exit /b 1
if not exist training\data mkdir training\data
if not exist public\models mkdir public\models
echo Copy LocomotivDataSet.xlsx into training\data\ then run scripts\train_model_windows.bat.
endlocal