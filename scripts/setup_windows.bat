@echo off
setlocal
cd /d "%~dp0.."
node --version
if errorlevel 1 (echo Install Node.js LTS from https://nodejs.org/ & exit /b 1)
call npm install
if errorlevel 1 exit /b 1
echo Setup complete. Run npm run dev.
endlocal