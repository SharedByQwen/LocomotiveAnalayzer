@echo off
setlocal
cd /d "%~dp0.."
if not exist training\data\LocomotivDataSet.xlsx (
  echo Dataset not found.
  echo Copy LocomotivDataSet.xlsx into training\data\
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  call scripts\setup_training_windows.bat
  if errorlevel 1 exit /b 1
)
call scripts\diagnose_training_windows.bat
call scripts\train_model_windows.bat
if errorlevel 1 exit /b 1
echo.
echo Training completed.
echo Evaluation report: training\output\evaluation_report.json
echo Test predictions: training\output\evaluation_predictions.csv
echo Final ONNX model: public\models\locomotive_model.onnx
echo Model metadata: public\models\metadata.json
echo Training log: logs\training.log
endlocal
