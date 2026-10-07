"""Configuration du backend.

Le mot de passe PostgreSQL n'est pas recopie : il est lu dans le .env du depot infra
(source unique), cherche a cote de ce depot ou dans un dossier "fortex" a cote.
"""

from __future__ import annotations

import os
from pathlib import Path

from sentinel import config as sentinel_config  # charge aussi le .env de ce depot

ROOT = sentinel_config.ROOT


def _infra_env() -> dict[str, str]:
    explicit = os.environ.get("FORTEX_INFRA_ENV")
    candidates = [Path(explicit)] if explicit else [
        ROOT.parent / "infra" / ".env",
        ROOT.parent / "fortex" / "infra" / ".env",
    ]
    for path in candidates:
        if path.exists():
            values = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip().strip('"').strip("'")
            return values
    return {}


_infra = _infra_env()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name) or _infra.get(name) or default


# PostgreSQL : nom, utilisateur et mot de passe viennent du depot infra. Hote et port sont ceux
# vus depuis la machine (le .env infra contient "postgres:5432", valable seulement dans Docker).
DB_HOST = os.environ.get("FORTEX_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("FORTEX_DB_PORT", "5433"))
DB_NAME = _get("POSTGRES_DB", "fortex")
DB_USER = _get("POSTGRES_USER", "fortex")
DB_PASSWORD = _get("POSTGRES_PASSWORD")

MQTT_HOST = sentinel_config.MQTT_HOST
MQTT_PORT = sentinel_config.MQTT_PORT
MQTT_USER = sentinel_config.MQTT_USER
MQTT_PASSWORD = sentinel_config.MQTT_PASSWORD
MQTT_CA_CERT = sentinel_config.MQTT_CA_CERT
SENSORS_TOPIC = sentinel_config.MQTT_TOPIC  # plusieurs topics separes par des virgules
COMMANDS_TOPIC = "sentinel/{node_id}/commands"
NODE_ID = sentinel_config.NODE_ID

# Meme jeton que celui utilise par l'IA pour POST /api/v1/alerts (vide = pas d'authentification).
API_TOKEN = sentinel_config.API_TOKEN
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "FORTEX_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

# Garde-fou de dernier recours (backend/messages.py:SafetyAlarm), distinct de l'IA predictive
SAFETY_ALARMS = os.environ.get("FORTEX_SAFETY_ALARMS", "1") != "0"
CRITICAL_TEMP = float(os.environ.get("FORTEX_CRITICAL_TEMP", "40"))
CRITICAL_GAS = float(os.environ.get("FORTEX_CRITICAL_GAS", "600"))
