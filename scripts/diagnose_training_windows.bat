@echo off
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
set "LOG=logs\training_environment.log"
echo ==== LocomotiveAnalayzer training environment ==== > "%LOG%"
echo Timestamp: %DATE% %TIME% >> "%LOG%"
echo Project: %CD% >> "%LOG%"
echo. >> "%LOG%"
echo [Python launcher] >> "%LOG%"
where py >> "%LOG%" 2>&1
py -0p >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo [Virtual environment] >> "%LOG%"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe --version >> "%LOG%" 2>&1
  .venv\Scripts\python.exe -m pip --version >> "%LOG%" 2>&1
  .venv\Scripts\python.exe -c "import numpy,pandas,sklearn,skl2onnx,onnx; print('numpy',numpy.__version__); print('pandas',pandas.__version__); print('scikit-learn',sklearn.__version__); print('skl2onnx',skl2onnx.__version__); print('onnx',onnx.__version__)" >> "%LOG%" 2>&1
) else (
  echo .venv not found. Run scripts\setup_training_windows.bat first. >> "%LOG%"
)
echo. >> "%LOG%"
echo [Dataset] >> "%LOG%"
if exist training\data\LocomotivDataSet.xlsx (
  dir training\data\LocomotivDataSet.xlsx >> "%LOG%" 2>&1
) else (
  echo Dataset missing: training\data\LocomotivDataSet.xlsx >> "%LOG%"
)
echo. >> "%LOG%"
echo Environment report saved to %LOG%
type "%LOG%"
endlocal
