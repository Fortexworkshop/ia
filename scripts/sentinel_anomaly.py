"""SENTINEL-X : maintenance predictive en temps reel sur les mesures de l'ESP8266.

python scripts/sentinel_anomaly.py                 # ecoute MQTT (SENTINEL_MQTT_*), alerte via l'API
python scripts/sentinel_anomaly.py --record        # enregistre aussi les mesures dans data/sensors.csv
python scripts/sentinel_anomaly.py --simulate      # sans ESP8266 : regime normal puis incident simule

Message MQTT attendu sur sentinel/<node_id>/sensors :
{"node_id": "SENTINEL-X-01", "temperature": 23.4, "humidity": 45.1, "gas": 312, "pir": 0}
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.alerts import AlertClient, Severity, build_alert  # noqa: E402
from sentinel.anomaly import SENSORS, AnomalyModel, StreamMonitor  # noqa: E402
from sentinel.debounce import Debouncer  # noqa: E402
from sentinel.simulate import incident_series  # noqa: E402

CRITICAL_SCORE = -0.05  # score tres negatif = anomalie marquee


class Pipeline:
    def __init__(self, model: AnomalyModel, alerts: AlertClient, consecutive: int, cooldown: float,
                 record: Path | None):
        self.monitor = StreamMonitor(model)
        self.alerts = alerts
        self.debouncer = Debouncer(consecutive, cooldown)
        self.record = record
        if record and not record.exists():
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("timestamp,node_id,temperature,humidity,gas,pir\n", encoding="utf-8")

    def handle(self, reading: dict) -> None:
        if any(reading.get(s) is None for s in SENSORS):
            print(f"[!] mesure incomplete ignoree : {reading}")
            return
        node = reading.get("node_id", config.NODE_ID)
        if self.record:
            with self.record.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), node,
                                        *(reading[s] for s in SENSORS), reading.get("pir", "")])

        score = self.monitor.push(reading)
        if score is None:
            print(f"  remplissage fenetre {len(self.monitor.buffer)}/{self.monitor.model.window}", end="\r")
            return
        flag = "ANOMALIE" if score < 0 else "normal"
        print(f"T={reading['temperature']:5.1f}  H={reading['humidity']:5.1f}  "
              f"gaz={reading['gas']:6.0f}  score={score:+.3f}  {flag}")

        if self.debouncer.update(score < 0, time.time()):
            severity = Severity.CRITICAL if score < CRITICAL_SCORE else Severity.WARNING
            self.alerts.send(build_alert(
                node, "anomaly", "ENV_ANOMALY", severity,
                "Derive anormale des capteurs environnementaux (risque surchauffe / fuite de gaz)",
                {"score": round(score, 4), "reading": {s: round(float(reading[s]), 2) for s in SENSORS},
                 "features": self.monitor.explain()},
            ))


def run_mqtt(pipeline: Pipeline) -> None:
    import paho.mqtt.client as mqtt

    def on_connect(client, userdata, flags, reason_code, properties):
        print(f"MQTT connecte ({reason_code}), abonnement a {config.MQTT_TOPIC}")
        client.subscribe(config.MQTT_TOPIC, qos=1)

    def on_message(client, userdata, msg):
        try:
            reading = json.loads(msg.payload)
        except ValueError:
            print(f"[!] payload non JSON sur {msg.topic}")
            return
        reading.setdefault("node_id", msg.topic.split("/")[1] if msg.topic.count("/") >= 2 else config.NODE_ID)
        pipeline.handle(reading)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sentinel-ia-{config.NODE_ID}")
    if config.MQTT_USER:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
    if config.MQTT_CA_CERT:
        client.tls_set(ca_certs=config.MQTT_CA_CERT)
    else:
        print("[!] SENTINEL_MQTT_CA_CERT non defini : connexion MQTT NON chiffree")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
    client.loop_forever()


def run_simulation(pipeline: Pipeline, interval: float) -> None:
    series = incident_series(700, start=200, rng=np.random.default_rng())
    print("Simulation : 200 mesures normales puis surchauffe lente + derive de gaz")
    for temp, hum, gas in series:
        pipeline.handle({"node_id": config.NODE_ID, "temperature": temp, "humidity": hum, "gas": gas, "pir": 0})
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--interval", type=float, default=0.05, help="pause entre mesures simulees (s)")
    parser.add_argument("--record", action="store_true", help=f"enregistre les mesures dans {config.SENSORS_CSV}")
    parser.add_argument("--consecutive", type=int, default=10, help="fenetres anormales de suite avant alerte")
    parser.add_argument("--cooldown", type=float, default=30.0)
    args = parser.parse_args()

    if not config.ANOMALY_MODEL.exists():
        sys.exit("Modele absent : lance d'abord python scripts/sentinel_train.py")
    model = AnomalyModel.load(config.ANOMALY_MODEL)
    alerts = AlertClient(config.API_URL, config.API_TOKEN, config.API_CA_CERT)
    pipeline = Pipeline(model, alerts, args.consecutive, args.cooldown,
                        config.SENSORS_CSV if args.record else None)
    try:
        if args.simulate:
            run_simulation(pipeline, args.interval)
        else:
            run_mqtt(pipeline)
    except KeyboardInterrupt:
        pass
    finally:
        alerts.flush()


if __name__ == "__main__":
    main()
