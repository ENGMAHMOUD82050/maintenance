@echo off
setlocal

REM ===============================
REM Detect project root (this .bat location)
REM ===============================
set "BASE_DIR=%~dp0"

REM ===============================
REM Database path (correct one)
REM ===============================
set "DB_PATH=%BASE_DIR%backend\maintenance.db"

REM ===============================
REM Backup folder
REM ===============================
set "BACKUP_DIR=%BASE_DIR%backups"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM ===============================
REM Get date using PowerShell (no WMIC)
REM ===============================
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "DATESTR=%%i"

set "ZIP_PATH=%BACKUP_DIR%\maintenance_%DATESTR%.zip"

REM ===============================
REM Validate DB exists
REM ===============================
if not exist "%DB_PATH%" (
  echo ERROR: Database file not found:
  echo "%DB_PATH%"
  echo.
  echo Tip: Make sure you ran run_server.bat at least once to create maintenance.db
  pause
  exit /b 1
)

REM ===============================
REM Create ZIP (Compress-Archive)
REM ===============================
powershell -NoProfile -Command "Compress-Archive -LiteralPath '%DB_PATH%' -DestinationPath '%ZIP_PATH%' -Force"

if errorlevel 1 (
  echo ERROR: Backup failed.
  pause
  exit /b 1
)

echo ====================================
echo Backup created successfully:
echo %ZIP_PATH%
echo ====================================
pause
endlocal
