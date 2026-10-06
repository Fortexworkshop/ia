# Lance tout le systeme FORTEX sur le PC Serveur Local, chaque brique dans sa fenetre.
#
# Usage : powershell -ExecutionPolicy Bypass -File scripts\start.ps1 [options]
#   -FakeEsp     ajoute un faux ESP8266 (tant que le vrai boitier n'est pas pret)
#   -Incident 60 avec -FakeEsp : derive surchauffe + gaz apres 60 mesures
#   -Admin       lance la plateforme eleves / pointage au lieu de la vision (une seule webcam)
#   -NoVision    ne lance pas la vision
#   -Infra / -Dashboard  chemins des depots infra et dev
#                (par defaut : a cote de ce depot, ou dans un dossier "fortex" a cote)
#   -DryRun      affiche les commandes sans rien lancer

param(
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
    foreach ($base in @($parent, (Join-Path $parent "fortex"))) {
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

# 2. IA
Launch "IA - maintenance predictive" $root "$py scripts/sentinel_anomaly.py"
if ($FakeEsp) {
    $opt = if ($Incident -ge 0) { " --incident $Incident" } else { "" }
    Launch "Faux ESP8266" $root "$py scripts/fake_esp.py --interval 1$opt"
}
if ($Admin) {
    Launch "IA - plateforme eleves" $root "$py scripts/sentinel_admin.py"
} elseif (-not $NoVision) {
    Launch "IA - vision" $root "$py scripts/sentinel_vision.py --whitelist"
}

# 3. Dashboard
if (Test-Path (Join-Path $Dashboard "package.json")) {
    $runner = if (Get-Command pnpm -ErrorAction SilentlyContinue) { "pnpm" } else { "npm" }
    Launch "Dashboard" $Dashboard "$runner run dev"
} else {
    Write-Host "[dashboard] introuvable ($Dashboard)" -ForegroundColor Yellow
}

Write-Host "`nDashboard : http://localhost:5173   Flux camera : http://localhost:8081/video" -ForegroundColor Green
if ($Admin) { Write-Host "Plateforme eleves : http://localhost:5000" -ForegroundColor Green }
