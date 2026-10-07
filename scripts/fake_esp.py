"""Faux ESP8266 : publie des mesures simulees sur Mosquitto, comme le vrai boitier.

python scripts/fake_esp.py                     # regime normal en continu (1 mesure / 2 s)
python scripts/fake_esp.py --incident 60       # derive (surchauffe + gaz) apres 60 mesures
python scripts/fake_esp.py --interval 0.1      # accelere pour une demo

Topic : sentinel/<node_id>/sensors (meme config SENTINEL_MQTT_* que sentinel_anomaly.py)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.simulate import incident_series, normal_series  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval", type=float, default=2.0, help="secondes entre deux mesures")
    parser.add_argument("--incident", type=int, help="declenche une derive apres N mesures")
    parser.add_argument("--count", type=int, default=100_000, help="nombre de mesures a publier")
    args = parser.parse_args()

    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fake-esp-{config.NODE_ID}")
    user = os.environ.get("ESP_MQTT_USER") or config.MQTT_USER  # compte du boitier (droits d'ecriture)
    password = os.environ.get("ESP_MQTT_PASSWORD") or config.MQTT_PASSWORD
    if user:
        client.username_pw_set(user, password)
    if config.MQTT_CA_CERT:
        client.tls_set(ca_certs=config.MQTT_CA_CERT)
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
    client.loop_start()

    rng = np.random.default_rng()
    series = (incident_series(args.count, args.incident, rng) if args.incident is not None
              else normal_series(args.count, rng))
    topic = f"sentinel/{config.NODE_ID}/sensors"
    print(f"Publication sur {config.MQTT_HOST}:{config.MQTT_PORT} topic {topic} (Ctrl+C pour arreter)")
    try:
        for i, (temp, hum, gas) in enumerate(series):
            payload = {"node_id": config.NODE_ID, "temperature": round(float(temp), 1),
                       "humidity": round(float(hum), 1), "gas": round(float(gas)), "pir": 0}
            client.publish(topic, json.dumps(payload), qos=1)
            tag = "  <- derive" if args.incident is not None and i >= args.incident else ""
            print(f"{i:5d} {payload}{tag}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
