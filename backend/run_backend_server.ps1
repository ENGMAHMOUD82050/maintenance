# backend\run_backend_server.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Maintenance System - PowerShell Runner" -ForegroundColor Cyan
Write-Host "Folder: $PWD" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Find python (prefer py)
$pyCmd = $null
try { $pyCmd = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $pyCmd) {
  try { $pyCmd = (Get-Command py -ErrorAction Stop).Source } catch {}
}

if (-not $pyCmd) {
  Write-Host "[ERROR] Python not found. Install Python 3.x then try again." -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

# Create venv if missing
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Yellow
  if ($pyCmd.ToLower().EndsWith("py.exe")) {
    & $pyCmd -3 -m venv .venv
  } else {
    & $pyCmd -m venv .venv
  }
}

if (-not (Test-Path $venvPy)) {
  Write-Host "[ERROR] venv python not found after creation." -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

# Install requirements
$req = Join-Path $PSScriptRoot "requirements.txt"
if (-not (Test-Path $req)) {
  Write-Host "[ERROR] requirements.txt not found in $PWD" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

Write-Host "[INFO] Installing requirements..." -ForegroundColor Yellow
& $venvPy -m pip install --upgrade pip | Out-Host
& $venvPy -m pip install -r $req | Out-Host

# Seed admin
$seed = Join-Path $PSScriptRoot "seed_admin.py"
if (Test-Path $seed) {
  Write-Host "[INFO] Seeding admin..." -ForegroundColor Yellow
  & $venvPy $seed | Out-Host
} else {
  Write-Host "[WARN] seed_admin.py not found, skipping." -ForegroundColor DarkYellow
}

# Run server
$app = Join-Path $PSScriptRoot "app.py"
if (-not (Test-Path $app)) {
  Write-Host "[ERROR] app.py not found in $PWD" -ForegroundColor Red
  Read-Host "Press Enter to exit"
  exit 1
}

Write-Host "==========================================" -ForegroundColor Green
Write-Host "[OK] Starting server..." -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

& $venvPy $app
Read-Host "Press Enter to exit"
