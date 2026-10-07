"""Boitier SENTINEL-X virtuel (remplace l'ESP8266 et les capteurs physiques).

python scripts/virtual_esp.py                  # http://localhost:8090 , 1 mesure / 2 s (comme le firmware)
python scripts/virtual_esp.py --interval 0.5   # accelere pour la demo

Se connecte au broker comme le vrai boitier : compte esp8266 (ESP_MQTT_USER / ESP_MQTT_PASSWORD),
MQTTS (SENTINEL_MQTT_CA_CERT), publie sur sentinel/<id>/sensors, ecoute sentinel/<id>/commands,
statut online/offline (LWT) sur sentinel/<id>/status.
"""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402
from sentinel.virtual_box import SCENARIOS, VirtualBox  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent / "sentinel" / "static" / "virtual_esp.html"


def make_mqtt(box: VirtualBox):
    import paho.mqtt.client as mqtt

    base = f"sentinel/{box.node_id}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"esp-{box.node_id}")
    user = os.environ.get("ESP_MQTT_USER") or config.MQTT_USER
    password = os.environ.get("ESP_MQTT_PASSWORD") or config.MQTT_PASSWORD
    if user:
        client.username_pw_set(user, password)
    if config.MQTT_CA_CERT:
        client.tls_set(ca_certs=config.MQTT_CA_CERT)
    client.will_set(f"{base}/status", "offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, reason_code, properties):
        box.mqtt_connected = not reason_code.is_failure
        box._log(f"MQTT {config.MQTT_HOST}:{config.MQTT_PORT} : {reason_code}")
        if box.mqtt_connected:
            c.publish(f"{base}/status", "online", qos=1, retain=True)
            c.subscribe(f"{base}/commands", qos=1)

    def on_disconnect(c, userdata, flags, reason_code, properties):
        box.mqtt_connected = False
        box._log("MQTT deconnecte")

    def on_message(c, userdata, msg):
        try:
            box.on_command(json.loads(msg.payload))
        except ValueError:
            box._log("commande JSON invalide ignoree")

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    client.reconnect_delay_set(1, 10)
    client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=15)
    client.loop_start()
    return client, f"{base}/sensors"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interval", type=float, default=2.0, help="secondes entre deux mesures")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()

    import uvicorn
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel

    box = VirtualBox(config.NODE_ID)
    client, topic = make_mqtt(box)
    settings = {"interval": args.interval}
    lock = threading.Lock()

    def loop():
        while True:
            with lock:
                payload = box.tick(time.time())
            if box.mqtt_connected:
                client.publish(topic, json.dumps(payload), qos=0)
                box.published += 1
            time.sleep(settings["interval"])

    threading.Thread(target=loop, daemon=True).start()

    app = FastAPI(title="Boitier SENTINEL-X virtuel")

    class Base(BaseModel):
        temperature: float | None = None
        humidity: float | None = None
        gas: float | None = None

    @app.get("/")
    def page():
        return FileResponse(PAGE)

    @app.get("/state")
    def state():
        with lock:
            return box.state() | {"interval": settings["interval"]}

    @app.post("/base")
    def set_base(values: Base):
        with lock:
            box.set_base(**values.model_dump())
        return {"ok": True}

    @app.post("/scenario/{name}")
    def scenario(name: str):
        if name != "normal" and name not in SCENARIOS:
            raise HTTPException(404, "scenario inconnu")
        with lock:
            box.start_scenario(None if name == "normal" else name)
        return {"ok": True}

    @app.post("/motion")
    def motion():
        with lock:
            box.trigger_motion(time.time())
        return {"ok": True}

    @app.post("/speed/{interval}")
    def speed(interval: float):
        settings["interval"] = min(max(interval, 0.2), 10.0)
        return {"interval": settings["interval"]}

    print(f"Boitier virtuel : http://localhost:{args.port}  ->  MQTT {config.MQTT_HOST}:{config.MQTT_PORT} topic {topic}")
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    finally:
        client.publish(f"sentinel/{box.node_id}/status", "offline", qos=1, retain=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
