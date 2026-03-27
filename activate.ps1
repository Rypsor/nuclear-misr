if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

Write-Host "Entorno listo. Usa: .\\activate.ps1" -ForegroundColor Green
