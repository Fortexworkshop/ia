# Lance tout le systeme FORTEX sur le PC Serveur Local, chaque brique dans sa fenetre.
#
# Usage : powershell -ExecutionPolicy Bypass -File scripts\start.ps1 [options]
#   (defaut)     boitier virtuel http://localhost:8090 (capteurs virtuels, meme protocole que l'ESP8266)
#   -RealEsp     pas de boitier virtuel : un vrai ESP8266 est branche
#   -FakeEsp     faux ESP en ligne de commande (sans interface) ; -Incident 60 : derive apres 60 mesures
#   -Admin       lance la plateforme d'acces / pointage au lieu de la vision (une seule webcam)
#   -NoVision    ne lance pas la vision
#   -Infra / -Dashboard  chemins de infra/ et dev/dashboard (par defaut : dans ce depot)
#   -DryRun      affiche les commandes sans rien lancer

param(
    [switch]$RealEsp,
    [switch]$FakeEsp,
    [int]$Incident = -1,
    [switch]$Admin,
    [switch]$NoVision,
    [string]$Infra,
    [string]$Dashboard,
    [switch]$DryRun
)

$root = Split-Path $PSScriptRoot -Parent
$parent = Split-Path $root -Parent
function Find($relative) {
    foreach ($base in @($root, $parent, (Join-Path $parent "fortex"))) {
        $candidate = Join-Path $base $relative
        if (Test-Path $candidate) { return $candidate }
    }
    return Join-Path $parent $relative
}
if (-not $Infra) { $Infra = Find "infra" }
if (-not $Dashboard) { $Dashboard = Find "dev\dashboard" }

function Launch($title, $dir, $command) {
    Write-Host "[$title] $command" -ForegroundColor Cyan
    if ($DryRun) { return }
    $script = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location '$dir'; $command"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $script
}

if (-not (Test-Path (Join-Path $root ".venv\Scripts\python.exe"))) {
    Write-Host "Lance d'abord scripts\setup.ps1" -ForegroundColor Red
    exit 1
}
$py = ".venv\Scripts\python.exe"

# 1. Infra : Mosquitto + PostgreSQL
if (Test-Path (Join-Path $Infra "docker-compose.yml")) {
    Write-Host "[infra] docker compose up -d ($Infra)" -ForegroundColor Cyan
    if (-not $DryRun) {
        if (-not (Test-Path (Join-Path $Infra ".env"))) {
            Write-Host "ATTENTION : $Infra\.env absent (copier .env.example et changer POSTGRES_PASSWORD)" -ForegroundColor Yellow
        }
        Push-Location $Infra
        docker compose up -d
        Pop-Location
        if ($LASTEXITCODE -ne 0) { Write-Host "Docker ne repond pas : demarre Docker Desktop" -ForegroundColor Red; exit 1 }
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "[infra] introuvable ($Infra) : Mosquitto doit deja tourner" -ForegroundColor Yellow
}

# 2. Backend (MQTT -> PostgreSQL + API REST/WebSocket pour le dashboard)
#    Conteneur fortex-backend du docker-compose infra s'il existe, sinon fenetre locale.
$backendInDocker = -not $DryRun -and (docker ps -q --filter "name=fortex-backend" 2>$null)
if ($backendInDocker) {
    Write-Host "[Backend FORTEX] conteneur Docker fortex-backend" -ForegroundColor Cyan
} else {
    Launch "Backend FORTEX" $root "$py scripts/backend.py"
    if (-not $DryRun) { Start-Sleep -Seconds 4 }
}

# 3. IA
Launch "IA - maintenance predictive" $root "$py scripts/sentinel_anomaly.py"
if (-not $RealEsp -and -not $FakeEsp) {
    Launch "Boitier virtuel" $root "$py scripts/virtual_esp.py"
}
if ($FakeEsp) {
    $opt = if ($Incident -ge 0) { " --incident $Incident" } else { "" }
    Launch "Faux ESP8266" $root "$py scripts/fake_esp.py --interval 1$opt"
}
if ($Admin) {
    Launch "IA - plateforme d'acces" $root "$py scripts/sentinel_admin.py"
} elseif (-not $NoVision) {
    Launch "IA - vision" $root "$py scripts/sentinel_vision.py --whitelist"
}

# 4. Dashboard
if (Test-Path (Join-Path $Dashboard "package.json")) {
    $runner = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { "npm" }
    # build de production + preview (en-tetes de securite, CSP) : jamais le serveur de dev en demo (OWASP A02/A03)
    Launch "Dashboard" $Dashboard "$runner run demo"
} else {
    Write-Host "[dashboard] introuvable ($Dashboard)" -ForegroundColor Yellow
}

Write-Host "`nDashboard : http://localhost:5173   Flux camera : http://localhost:8081/video" -ForegroundColor Green
Write-Host "API backend : http://localhost:8080/docs" -ForegroundColor Green
Write-Host "Grafana (supervision / MCO) : http://localhost:3001  (admin / GRAFANA_ADMIN_PASSWORD de infra\.env)" -ForegroundColor Green
if (-not $RealEsp -and -not $FakeEsp) { Write-Host "Boitier virtuel : http://localhost:8090" -ForegroundColor Green }
if ($Admin) { Write-Host "Plateforme d'acces : http://localhost:5000" -ForegroundColor Green }
