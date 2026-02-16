@echo off
cd /d "%~dp0backend"
powershell -NoProfile -ExecutionPolicy Bypass -File "run_backend_server.ps1"
pause
