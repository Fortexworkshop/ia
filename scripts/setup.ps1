# Installation complete de FORTEX sur le PC Serveur Local (une seule fois).
# Usage : powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-ServerIp 192.168.10.1]
# Prerequis : Python 3.11, Git for Windows (Git Bash), Docker Desktop demarre, Node.js

param([string]$ServerIp = "192.168.10.1")

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

Step "Configuration (secrets, certificats TLS, comptes MQTT, .env, firmware)"
& $py scripts/configure.py --server-ip $ServerIp
Check "configuration"

Step "Tests"
& $py -m pytest -q
Check "tests"

$dashboard = Join-Path $root "dev\dashboard"
if (Test-Path (Join-Path $dashboard "package.json")) {
    Step "Dashboard : dependances Node"
    if (-not (Test-Path (Join-Path $dashboard "node_modules"))) {
        Push-Location $dashboard
        if (Get-Command pnpm -ErrorAction SilentlyContinue) { pnpm install } else { npm install --no-audit --no-fund }
        Pop-Location
    } else { Write-Host "deja installees" }
}

Step "Stack Docker (Mosquitto MQTTS, PostgreSQL, Prometheus, Grafana)"
Push-Location (Join-Path $root "infra")
docker compose up -d
Check "docker compose"
Start-Sleep -Seconds 8
# compte PostgreSQL en lecture seule pour Grafana (idempotent, aussi pour une base deja creee)
docker compose exec -T postgres sh /docker-entrypoint-initdb.d/02-grafana-readonly.sh
Pop-Location

Write-Host "`nInstallation terminee. Lancement : powershell -ExecutionPolicy Bypass -File scripts\start.ps1" -ForegroundColor Green
