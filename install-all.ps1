python -m venv .venv
& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements\gui.txt
python -m pip install -e .

Write-Host "Instalacion completa finalizada." -ForegroundColor Green
Write-Host "Siguiente paso: .\\activate.ps1" -ForegroundColor Yellow
