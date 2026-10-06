# Installation de la brique IA sur le PC Serveur Local (une seule fois).
# Usage : powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Check($what) {
    if ($LASTEXITCODE -ne 0) { Write-Host "ECHEC : $what" -ForegroundColor Red; exit 1 }
}

Step "Python 3.11"
if (-not (Test-Path .venv\Scripts\python.exe)) {
    py -3.11 --version
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python 3.11 introuvable. Installe-le puis relance : winget install Python.Python.3.11" -ForegroundColor Red
        exit 1
    }
    py -3.11 -m venv .venv
    Check "creation du venv"
}
$py = Join-Path $root ".venv\Scripts\python.exe"

Step "Dependances Python (plusieurs minutes la premiere fois : PyTorch)"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements.txt --quiet
Check "pip install"

Step "Modeles pre-entraines (visage, main, YOLOv8n)"
& $py scripts/download_models.py
Check "telechargement des modeles"

Step "Modele de maintenance predictive"
if (Test-Path models\anomaly.joblib) {
    Write-Host "deja entraine (relancer scripts/sentinel_train.py pour le refaire)"
} else {
    & $py scripts/sentinel_train.py
    Check "entrainement"
}

Step "Configuration"
if (Test-Path .env) {
    Write-Host ".env deja present"
} else {
    Copy-Item .env.example .env
    Write-Host ".env cree a partir de .env.example"
}

Step "Tests"
& $py -m pytest -q
Check "tests"

$parent = Split-Path $root -Parent
$dashboard = @((Join-Path $parent "dev\dashboard"), (Join-Path $parent "fortex\dev\dashboard")) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if ($dashboard) {
    Step "Dashboard ($dashboard)"
    if (-not (Test-Path (Join-Path $dashboard ".env"))) {
        "VITE_API_URL=`nVITE_CAMERA_URL=http://localhost:8081/video" | Set-Content -Encoding ascii (Join-Path $dashboard ".env")
        Write-Host ".env du dashboard cree (camera : http://localhost:8081/video)"
    }
    if (-not (Test-Path (Join-Path $dashboard "node_modules"))) {
        Push-Location $dashboard
        if (Get-Command pnpm -ErrorAction SilentlyContinue) { pnpm install } else { npm install --no-audit --no-fund }
        Pop-Location
    }
}

Write-Host "`nInstallation terminee. Lancement : powershell -ExecutionPolicy Bypass -File scripts\start.ps1" -ForegroundColor Green
