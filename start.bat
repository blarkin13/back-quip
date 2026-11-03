
@echo off
setlocal
cd /d "%~dp0"
echo Starting Back Quip...

if not exist .venv\Scripts\python.exe (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Python 3.10+ is required.
    pause
    exit /b 1
  )
  py -m venv .venv
)

if not exist .venv\Scripts\python.exe (
  echo Could not create Python environment.
  pause
  exit /b 1
)

rem Install prebuilt Windows CPU binaries instead of compiling.
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :fail

.venv\Scripts\python.exe -m pip install --only-binary=llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu -r requirements.txt
if errorlevel 1 goto :fail

.venv\Scripts\python.exe launcher.py
if errorlevel 1 (
  echo Back Quip could not start.
  pause
  exit /b 1
)

exit /b 0

:fail
echo Dependency installation failed.
echo Check that a compatible prebuilt wheel exists for your Python version.
pause
exit /b 1
