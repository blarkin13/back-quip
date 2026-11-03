@echo off
setlocal
cd /d "%~dp0"
echo Starting Back Quip...
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Python 3.10-3.12 is required. Install Python from https://python.org/downloads/
    pause
    exit /b 1
  )
  py -3.11 -m venv .venv 2>nul
  if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv 2>nul
  if not exist ".venv\Scripts\python.exe" py -3.10 -m venv .venv 2>nul
)
if not exist ".venv\Scripts\python.exe" (
  echo Could not create Python environment. Python 3.10, 3.11, or 3.12 is required.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -q --upgrade pip
if errorlevel 1 goto :fail
rem Install the binary build before the other dependencies; never compile on a user's Windows PC.
.venv\Scripts\python.exe -m pip install --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu "llama-cpp-python>=0.3.16,<0.4"
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail
.venv\Scripts\python.exe launcher.py
if errorlevel 1 goto :fail
exit /b 0
:fail
echo.
echo Setup failed. A prebuilt engine wheel may not support this Python version.
echo Use 64-bit Python 3.10-3.12 and rerun start.bat.
pause
exit /b 1
