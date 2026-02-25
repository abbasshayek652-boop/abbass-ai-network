param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot/.."),
    [string]$VenvPath = "$ProjectRoot/.venv"
)

python -m venv $VenvPath
& "$VenvPath/Scripts/Activate.ps1"
python -m pip install --upgrade pip
pip install -r "$ProjectRoot/requirements.txt"

Write-Host "Environment ready."
Write-Host "Activate with:`n  & $VenvPath/Scripts/Activate.ps1"
Write-Host "Run services:`n  uvicorn gateway:app --reload --port 8000"
Write-Host "Run tests:`n  pytest -q"
