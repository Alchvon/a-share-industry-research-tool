@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0work\.venv\Scripts\python.exe" (
  echo First-time setup is required.
  echo Please run the first-time setup file in this folder.
  pause
  exit /b 1
)

echo Opening A-share Industry Research Tool...
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/health' -TimeoutSec 2 ^| Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  start "A-share Industry Research Tool" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backend\run_stable.ps1"
  timeout /t 4 /nobreak >nul
)

start "" "%~dp0frontend\index.html"
echo The browser has been opened. You can close this window.
timeout /t 3 /nobreak >nul
