"""Controle de securite de la stack FORTEX (preuve pour la soutenance et le rapport d'audit).

python scripts/check_security.py

Verifie, sur le broker et le backend reels :
  1. le port MQTT en clair (1883) est ferme
  2. une connexion MQTTS anonyme est refusee
  3. un mauvais mot de passe est refuse
  4. le certificat du broker est valide (CA FORTEX) et la session est chiffree (TLS 1.2+)
  5. le compte du boitier publie ses mesures, recues par le backend (bout en bout)
  6. l'ACL empeche le compte serveur de publier de fausses mesures
  7. POST /api/v1/alerts refuse une requete sans jeton
"""

import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sentinel import config  # noqa: E402

API = config.API_URL or "http://localhost:8080"
results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"[{'OK ' if ok else 'ECHEC'}] {name}" + (f" ({detail})" if detail else ""))


def mqtt_connect(user=None, password=None, tls=True, port=None):
    """Renvoie (connecte, code de raison, client)."""
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"audit-{uuid.uuid4().hex[:6]}")
    state = {}
    client.on_connect = lambda c, u, f, rc, p: state.update(rc=rc)
    if user:
        client.username_pw_set(user, password)
    if tls:
        client.tls_set(ca_certs=config.MQTT_CA_CERT)
    try:
        client.connect(config.MQTT_HOST, port or config.MQTT_PORT, keepalive=10)
    except Exception as exc:
        return False, exc.__class__.__name__, client
    client.loop_start()
    for _ in range(30):
        if "rc" in state:
            break
        time.sleep(0.1)
    rc = state.get("rc")
    return bool(rc is not None and not rc.is_failure), str(rc), client


def received(temperature: float) -> bool:
    """La mesure marquee par cette temperature unique est-elle arrivee au backend ?"""
    with urllib.request.urlopen(f"{API}/api/v1/readings?limit=50", timeout=3) as resp:
        return any(abs(r["temp"] - temperature) < 1e-6 for r in json.load(resp))


def marker() -> float:
    return round(10 + int(uuid.uuid4().int % 1000) / 100, 2)  # unique, 2 decimales (NUMERIC(5,2) en base)


def main() -> None:
    if not config.MQTT_CA_CERT:
        sys.exit("SENTINEL_MQTT_CA_CERT non defini dans .env : TLS non configure")
    print(f"Broker {config.MQTT_HOST}:{config.MQTT_PORT}, API {API}\n")

    # 1. port en clair
    with socket.socket() as s:
        s.settimeout(2)
        closed = s.connect_ex((config.MQTT_HOST, 1883)) != 0
    check("Port MQTT en clair 1883 ferme", closed)

    # 2. anonyme
    ok, rc, c = mqtt_connect()
    c.loop_stop()
    check("Connexion MQTTS anonyme refusee", not ok, rc)

    # 3. mauvais mot de passe
    ok, rc, c = mqtt_connect(config.MQTT_USER, "mauvais-mot-de-passe")
    c.loop_stop()
    check("Mauvais mot de passe refuse", not ok, rc)

    # 4. certificat et chiffrement
    context = ssl.create_default_context(cafile=config.MQTT_CA_CERT)
    try:
        with socket.create_connection((config.MQTT_HOST, config.MQTT_PORT), timeout=3) as raw:
            with context.wrap_socket(raw, server_hostname=config.MQTT_HOST) as tls:
                cert = tls.getpeercert()
                issuer = dict(x[0] for x in cert["issuer"]).get("commonName")
                check("Certificat du broker valide et session chiffree", True,
                      f"{tls.version()}, {tls.cipher()[0]}, emis par {issuer}")
    except ssl.SSLError as exc:
        check("Certificat du broker valide et session chiffree", False, str(exc))

    # 5. bout en bout avec le compte du boitier
    esp_user = os.environ.get("ESP_MQTT_USER", "esp8266")
    esp_password = os.environ.get("ESP_MQTT_PASSWORD", "")
    mark = marker()
    ok, rc, esp = mqtt_connect(esp_user, esp_password)
    if ok:
        payload = {"node_id": "AUDIT", "temperature": mark, "humidity": 40.0, "gas": 250, "pir": 0}
        esp.publish("sentinel/AUDIT/sensors", json.dumps(payload), qos=1).wait_for_publish(3)
        time.sleep(1.5)
    esp.loop_stop()
    esp.disconnect()
    check("Compte boitier : mesure chiffree recue par le backend", ok and received(mark), f"connexion {rc}")

    # 6. ACL : le compte serveur ne peut pas injecter de mesures
    mark = marker()
    ok, rc, srv = mqtt_connect(config.MQTT_USER, config.MQTT_PASSWORD)
    if ok:
        fake = {"node_id": "PIRATE", "temperature": mark, "humidity": 1.0, "gas": 1000, "pir": 1}
        srv.publish("sentinel/PIRATE/sensors", json.dumps(fake), qos=0)
        time.sleep(1.5)
    srv.loop_stop()
    srv.disconnect()
    check("ACL : le compte serveur ne peut pas publier de fausses mesures",
          ok and not received(mark), f"connexion {rc}")

    # 7. API protegee par jeton
    request = urllib.request.Request(f"{API}/api/v1/alerts", method="POST",
                                     data=json.dumps({"type": "PIRATE"}).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=3)
        status = 201
    except urllib.error.HTTPError as exc:
        status = exc.code
    check("POST /api/v1/alerts sans jeton refuse", status == 401, f"HTTP {status}")

    print(f"\n{sum(results)}/{len(results)} controles reussis")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
