# Run the API locally without Docker (uses .env for configuration).
# Usage:  .\run_local.ps1  [-Port 8000]
param([int]$Port = 8000)

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    & "C:\Users\marya\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv (Join-Path $PSScriptRoot ".venv")
    & $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
