@echo off
setlocal
cd /d "%~dp0"

echo A-share Industry Research Tool - First-time Setup
where py >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python 3.11 or newer is required.
  echo Please install Python from https://www.python.org/downloads/
  echo During installation, select "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist "work\.venv\Scripts\python.exe" (
  echo Creating local runtime...
  py -3 -m venv "work\.venv"
  if errorlevel 1 (
    echo Failed to create the local runtime.
    pause
    exit /b 1
  )
)

echo Installing required components. Internet access is needed for this step.
"work\.venv\Scripts\python.exe" -m pip install --upgrade pip
"work\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
  echo.
  echo Setup did not finish. Check the internet connection and run this file again.
  pause
  exit /b 1
)

echo.
echo Setup complete. Starting the application...
call "%~dp0Start.cmd"
