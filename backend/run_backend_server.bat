@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo ==========================================
echo Maintenance System - Backend Runner
echo Folder: %CD%
echo ==========================================

REM --- Detect Python ---
set "PYEXE="
where python >nul 2>nul
if not errorlevel 1 set "PYEXE=python"

if "%PYEXE%"=="" (
  where py >nul 2>nul
  if not errorlevel 1 set "PYEXE=py"
)

if "%PYEXE%"=="" (
  echo [ERROR] Python not found. Install Python 3.x then try again.
  pause
  exit /b 1
)

REM --- Create venv if missing ---
if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating virtual environment (.venv)...
  if "%PYEXE%"=="py" (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )

  if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

REM --- Activate venv ---
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate virtual environment.
  pause
  exit /b 1
)

REM --- Install requirements ---
if not exist "requirements.txt" (
  echo [ERROR] requirements.txt not found in:
  echo %CD%
  pause
  exit /b 1
)

echo [INFO] Installing requirements...
python -m pip install --upgrade pip >nul 2>nul

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [WARN] First attempt failed, retrying once...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install requirements. Check internet/proxy.
    pause
    exit /b 1
  )
)

REM --- Seed admin ---
if exist "seed_admin.py" (
  echo [INFO] Seeding admin user...
  python seed_admin.py
) else (
  echo [WARN] seed_admin.py not found, skipping.
)

REM --- Run server ---
echo ==========================================
echo [OK] Starting server...
echo Open: http://127.0.0.1:5000
echo ==========================================
python app.py

pause
