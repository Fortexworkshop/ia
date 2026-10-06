"""Configuration par variables d'environnement (aucun secret dans le code).

Copier .env.example en .env, ou definir les variables dans le shell / docker-compose.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
DATA_DIR = ROOT / "data"


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Lecture minimale d'un fichier .env (CLE=valeur), sans ecraser l'environnement existant."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


NODE_ID = _env("SENTINEL_NODE_ID", "SENTINEL-X-01")

# --- API de l'equipe DEV : POST {API_URL}/api/v1/alerts ---------------------
API_URL = _env("SENTINEL_API_URL")            # ex: https://192.168.10.1:8443 (vide = mode hors ligne)
API_TOKEN = _env("SENTINEL_API_TOKEN")        # envoye en "Authorization: Bearer ..."
API_CA_CERT = _env("SENTINEL_API_CA_CERT")    # CA de la stack (certificat auto-signe)

# --- Broker MQTT (capteurs ESP8266) ---------------------------------------
MQTT_HOST = _env("SENTINEL_MQTT_HOST", "localhost")
MQTT_PORT = int(_env("SENTINEL_MQTT_PORT", "1883"))
MQTT_TOPIC = _env("SENTINEL_MQTT_TOPIC", "sentinel/+/sensors")
MQTT_USER = _env("SENTINEL_MQTT_USER")
MQTT_PASSWORD = _env("SENTINEL_MQTT_PASSWORD")
MQTT_CA_CERT = _env("SENTINEL_MQTT_CA_CERT")  # vide = pas de TLS (a eviter hors debug)

# --- Vision ---------------------------------------------------------------
YOLO_MODEL = _env("SENTINEL_YOLO_MODEL", str(MODELS_DIR / "yolov8n.pt"))
FRAME_SIZE = (640, 480)                       # bridage impose par le sujet
STREAM_PORT = int(_env("SENTINEL_STREAM_PORT", "8081"))

# --- Maintenance predictive -----------------------------------------------
ANOMALY_MODEL = MODELS_DIR / "anomaly.joblib"
SENSORS_CSV = DATA_DIR / "sensors.csv"
