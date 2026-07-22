@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. Install the version listed in package.json.
  pause
  exit /b 1
)
if not exist node_modules call npm install
if errorlevel 1 exit /b 1
start "" "http://localhost:5173"
call npm run dev
pause
