$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python 3 was not found on PATH. Install Python 3.10 or newer and rerun install.ps1."
}

if (-not (Test-Path -LiteralPath ".venv")) {
    & $python.Source -m venv .venv
}

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path -LiteralPath "config.yaml")) {
    Copy-Item -LiteralPath "config.example.yaml" -Destination "config.yaml"
    Write-Host "Created config.yaml. Add your Football-Data.org API key before running the skill."
}

Write-Host "Installed soccer-lottery-test in $root"
Write-Host "Python: $venvPython"
