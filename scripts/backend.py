"""Lance le backend FORTEX : MQTT (capteurs) + API REST/WebSocket + PostgreSQL.

python scripts/backend.py                 # http://localhost:8080 , WebSocket ws://localhost:8080/ws
python scripts/backend.py --memory        # sans PostgreSQL (donnees en memoire)
python scripts/backend.py --host 0.0.0.0  # accessible depuis le reseau de la table

PostgreSQL : nom / utilisateur / mot de passe lus dans le .env du depot infra.
Le port 5432 du conteneur doit etre publie sur la machine (5433 par defaut, FORTEX_DB_PORT).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config  # noqa: E402
from backend.app import Hub, Service, create_app  # noqa: E402
from backend.messages import SafetyAlarm  # noqa: E402
from backend.mqtt_bridge import MqttBridge  # noqa: E402
from backend.store import MemoryStore, PostgresStore  # noqa: E402


def make_store(memory: bool):
    if memory:
        return MemoryStore()
    if not config.DB_PASSWORD:
        print("[db] mot de passe PostgreSQL introuvable (.env du depot infra) : stockage en memoire")
        return MemoryStore()
    try:
        store = PostgresStore(config.DB_HOST, config.DB_PORT, config.DB_NAME, config.DB_USER, config.DB_PASSWORD)
        print(f"[db] connecte : {store.backend}")
        return store
    except Exception as exc:
        print(f"[db] PostgreSQL injoignable sur {config.DB_HOST}:{config.DB_PORT} ({exc.__class__.__name__}) : "
              "stockage en memoire. Le port est-il publie dans docker-compose (5433:5432) ?")
        return MemoryStore()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--memory", action="store_true", help="ne pas utiliser PostgreSQL")
    args = parser.parse_args()

    import uvicorn

    safety = SafetyAlarm(config.CRITICAL_TEMP, config.CRITICAL_GAS) if config.SAFETY_ALARMS else None
    service = Service(make_store(args.memory), Hub(), safety,
                      node_id=config.NODE_ID)
    bridge = MqttBridge(service, config.MQTT_HOST, config.MQTT_PORT, config.SENSORS_TOPIC,
                        config.MQTT_USER, config.MQTT_PASSWORD, config.MQTT_CA_CERT)
    service.publish = bridge.publish
    if not config.API_TOKEN:
        print("[api] SENTINEL_API_TOKEN vide : POST /api/v1/alerts sans authentification")

    app = create_app(service, config.API_TOKEN, config.CORS_ORIGINS, mqtt_status=lambda: bridge.connected,
                     on_startup=bridge.start, on_shutdown=bridge.stop)
    print(f"API : http://localhost:{args.port}/docs   WebSocket : ws://localhost:{args.port}/ws")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
