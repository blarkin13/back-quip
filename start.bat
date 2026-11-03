@echo off
setlocal
cd /d "%~dp0"
echo Starting Back Quip...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-runtime.ps1"
if errorlevel 1 (
  echo.
  echo Local AI setup was not completed. See instructions above.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Python 3.10+ is required. Download it from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  py -m venv .venv
)
if not exist .venv\Scripts\python.exe (
  echo Could not create the Python environment. Install Python 3.10+ and try again.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
.venv\Scripts\python.exe launcher.py
if errorlevel 1 (
  echo Back Quip could not start.
  pause
  exit /b 1
)
