$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot "work\.venv\Scripts\python.exe"

$env:PYTHONPATH = $PSScriptRoot
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
