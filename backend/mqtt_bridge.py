"""Pont MQTT : abonnement aux capteurs ESP8266 et publication des commandes d'actionneurs."""

from __future__ import annotations

import json

from sentinel.sensors import topics


class MqttBridge:
    def __init__(self, service, host: str, port: int, topic: str, user: str = "", password: str = "",
                 ca_cert: str = ""):
        import paho.mqtt.client as mqtt

        self.service = service
        self.topic = topic
        self.host, self.port = host, port
        self.connected = False
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fortex-backend")
        if user:
            self.client.username_pw_set(user, password)
        if ca_cert:
            self.client.tls_set(ca_certs=ca_cert)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(1, 10)

    def start(self) -> None:
        self.client.connect_async(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict) -> bool:
        if not self.connected:
            return False
        return self.client.publish(topic, json.dumps(payload), qos=1).rc == 0

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self.connected = not reason_code.is_failure
        print(f"[mqtt] connecte a {self.host}:{self.port} ({reason_code}), abonnement {self.topic}")
        for topic in topics(self.topic):
            client.subscribe(topic, qos=1)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected = False
        print(f"[mqtt] deconnecte ({reason_code}), nouvelle tentative...")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
        except ValueError:
            print(f"[mqtt] payload non JSON ignore sur {msg.topic}")
            return
        parts = msg.topic.split("/")
        node = payload.get("node_id") or (parts[1] if parts[0] == "sentinel" and len(parts) >= 3 else "simulateur")
        try:
            if not self.service.ingest_reading(node, payload):
                print(f"[mqtt] mesure incomplete ignoree : {payload}")
        except Exception as exc:  # une base indisponible ne doit pas tuer le thread MQTT
            print(f"[mqtt] erreur d'enregistrement : {exc}")
