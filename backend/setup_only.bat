@echo off
setlocal

cd /d "%~dp0"

set PYEXE=
where python >nul 2>nul && set PYEXE=python
if "%PYEXE%"=="" (
  where py >nul 2>nul && set PYEXE=py -3
)

if "%PYEXE%"=="" (
  echo [ERROR] Python not found. Please install Python 3.x first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating venv...
  %PYEXE% -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo [INFO] Installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [OK] Setup completed.
pause
