# FORTEX — Infrastructure

Infrastructure du projet FORTEX réalisé dans le cadre du Workshop EPSI Bac+4 2026.

## Objectif

Mettre en place l'infrastructure du PC Serveur Local permettant de faire fonctionner les différentes briques du projet FORTEX.

## Composants prévus

- Docker / Docker Compose
- Mosquitto MQTT
- Base de données PostgreSQL
- Backend / API
- Réseau dédié à la table
- Sécurisation des flux
- Monitoring et MCO

## Architecture

PC Serveur Local
- Windows 11
- WSL 2
- Docker Desktop

## Équipe

Infrastructure — Fortexworkshop

## Stack securisee (branche feat/backend-tls)

Mosquitto en **MQTTS (port 8883)**, comptes obligatoires et droits par compte, backend FORTEX
conteneurise (depot `ia`), PostgreSQL non expose, conteneurs durcis.

```bash
cp .env.example .env                 # puis remplir les mots de passe et le jeton
./scripts/gen-certs.sh 192.168.10.1  # CA + certificat du broker (IP du PC serveur)
./scripts/gen-mqtt-users.sh          # comptes esp8266 et serveur -> mqtt-users.env
docker compose up -d --build         # mosquitto + postgres + backend (http://localhost:8080/docs)
docker compose --profile simulation up -d   # optionnel : simulateur IoT
```

- `IA_DIR` (dans `.env`) : chemin du depot `ia`, qui contient le `Dockerfile` du backend.
- `certs/ca.crt` est a copier dans le firmware ESP8266 et a indiquer a l'IA (`SENTINEL_MQTT_CA_CERT`).
- Secrets jamais commites : `.env`, `certs/`, `mqtt-users.env`, `mosquitto/config/passwd`.
- Verification : `python scripts/check_security.py` dans le depot `ia` (7 controles).
