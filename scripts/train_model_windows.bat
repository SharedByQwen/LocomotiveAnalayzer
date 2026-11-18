@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\activate.bat (echo Run setup_training_windows.bat first. & exit /b 1)
call .venv\Scripts\activate.bat
python training\train_model.py --dataset training\data\LocomotivDataSet.xlsx
if errorlevel 1 (echo Training failed. Check logs\training.log. & exit /b 1)
echo Model exported into public\models\
endlocal