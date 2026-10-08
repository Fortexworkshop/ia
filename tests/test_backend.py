import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import CommandIn, Hub, Service, create_app  # noqa: E402
from backend.messages import SafetyAlarm, alert_message, parse_sensor_payload  # noqa: E402
from backend.store import MemoryStore  # noqa: E402

INTRUSION = {"node_id": "SX-01", "source": "vision", "type": "INTRUSION", "severity": "critical",
             "message": "intrus", "timestamp": "2026-10-06T14:00:00+02:00", "data": {"intruders": 2}}


def make(token="", publish=None):
    service = Service(MemoryStore(), Hub(), SafetyAlarm(40, 600), publish=publish, node_id="SX-01")
    return service, create_app(service, api_token=token)


def test_parse_sensor_payload_accepts_both_namings():
    assert parse_sensor_payload({"temperature": 22, "humidity": 40, "gas": 300, "pir": 1}) == \
        {"temperature": 22.0, "humidity": 40.0, "gas": 300.0, "pir": 1}
    assert parse_sensor_payload({"temp": 22, "hum": 40, "gas": 300})["pir"] == 0
    assert parse_sensor_payload({"temp": 22}) is None
    assert parse_sensor_payload({"temp": "abc", "hum": 1, "gas": 1}) is None


def test_alert_message_matches_dashboard_contract():
    msg = alert_message({**INTRUSION, "id": 3})
    assert msg["type"] == "alert" and msg["kind"] == "intrusion" and msg["level"] == "critical"
    assert msg["value"] == 2 and msg["device_id"] == "SX-01" and isinstance(msg["ts"], int)
    anomaly = alert_message({"type": "ENV_ANOMALY", "data": {"reading": {"temperature": 31.2}}})
    assert anomaly["kind"] == "anomalie" and anomaly["value"] == 31.2 and anomaly["unit"] == "°C"


def test_safety_alarm_cooldown_and_pir_edge():
    watcher = SafetyAlarm(40, 600, cooldown_s=30)
    hot = {"temperature": 41, "humidity": 40, "gas": 300, "pir": 0}
    assert [a["type"] for a in watcher.check("n", hot, now=0)] == ["TEMPERATURE"]
    assert watcher.check("n", hot, now=10) == []          # delai anti-repetition
    assert len(watcher.check("n", hot, now=31)) == 1
    calm = {"temperature": 22, "humidity": 40, "gas": 300, "pir": 1}
    assert [a["type"] for a in watcher.check("n", calm, now=40)] == ["PRESENCE"]
    assert watcher.check("n", calm, now=100) == []         # pas de front montant


def test_post_alert_requires_token():
    _, app = make(token="s3cret")
    client = TestClient(app)
    assert client.post("/api/v1/alerts", json=INTRUSION).status_code == 401
    res = client.post("/api/v1/alerts", json=INTRUSION, headers={"Authorization": "Bearer s3cret"})
    assert res.status_code == 201
    alerts = client.get("/api/v1/alerts").json()
    assert alerts[0]["kind"] == "intrusion" and alerts[0]["id"] == res.json()["id"]
    auth = {"Authorization": "Bearer s3cret"}
    assert client.post(f"/api/v1/alerts/{res.json()['id']}/ack").status_code == 401  # anonyme refuse
    assert client.post(f"/api/v1/alerts/{res.json()['id']}/ack", headers=auth).json()["acknowledged"]
    assert client.post("/api/v1/alerts/999/ack", headers=auth).status_code == 404


def test_invalid_alert_rejected():
    _, app = make()
    assert TestClient(app).post("/api/v1/alerts", json={"type": "X", "severity": "panique"}).status_code == 422


def test_readings_and_critical_threshold_alert():
    service, app = make()
    client = TestClient(app)
    assert service.ingest_reading("SX-01", {"temperature": 23, "humidity": 45, "gas": 310, "pir": 0})
    assert service.ingest_reading("SX-01", {"temperature": 42, "humidity": 45, "gas": 310, "pir": 0})
    assert not service.ingest_reading("SX-01", {"oops": 1})
    readings = client.get("/api/v1/readings").json()
    assert [r["temp"] for r in readings] == [23.0, 42.0]
    assert client.get("/api/v1/alerts").json()[0]["kind"] == "temperature"
    assert client.get("/api/v1/devices").json()[0]["node_id"] == "SX-01"


def test_command_publishes_on_mqtt():
    sent = []
    _, app = make(publish=lambda topic, payload: sent.append((topic, payload)) or True)
    res = TestClient(app).post("/api/v1/commands", json={"actuator": "buzzer", "state": True})
    assert res.json() == {"delivered": True}
    assert sent == [("sentinel/SX-01/commands", {"actuator": "buzzer", "state": True})]


def test_command_without_mqtt_is_not_delivered():
    service, _ = make()
    assert service.command(CommandIn(actuator="led", state=False)) is False


def test_websocket_receives_alerts_and_readings():
    service, app = make()
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        client.post("/api/v1/test/heat")
        assert ws.receive_json()["kind"] == "temperature"
        client.post("/api/v1/alerts", json=INTRUSION)
        assert ws.receive_json()["kind"] == "intrusion"
        # l'intrusion declenche l'alarme physique : buzzer puis LED
        assert [ws.receive_json()["cmd"]["actuator"] for _ in range(2)] == ["buzzer", "led"]
        service.ingest_reading("SX-01", {"temp": 22.5, "hum": 40, "gas": 300})  # depuis un autre thread (MQTT)
        msg = ws.receive_json()
        assert msg["type"] == "reading" and msg["temp"] == 22.5


def test_health_and_unknown_test():
    _, app = make()
    client = TestClient(app)
    assert client.get("/health").json()["database"] == "memoire"
    assert client.post("/api/v1/test/volcan").status_code == 404


def test_safety_alarm_can_be_disabled():
    service = Service(MemoryStore(), Hub(), None, node_id="SX-01")
    service.ingest_reading("SX-01", {"temperature": 90, "humidity": 40, "gas": 900, "pir": 1})
    assert service.store.recent_alerts(10) == []


def test_alert_without_value_has_no_unit():
    assert alert_message({"type": "ENV_ANOMALY", "data": {}})["unit"] == ""


def test_metrics_prometheus_format(tmp_path):
    service, _ = make()
    log = tmp_path / "mosquitto.log"
    log.write_text("x" * 1234)
    app = create_app(service, mosquitto_log=log)
    client = TestClient(app)
    service.ingest_reading("SX-01", {"temperature": 23, "humidity": 45, "gas": 300, "pir": 0})
    service.ingest_reading("SX-01", {"oops": 1})
    client.post("/api/v1/alerts", json=INTRUSION)
    text = client.get("/metrics").text
    assert "fortex_readings_total 1" in text
    assert "fortex_readings_rejected_total 1" in text
    assert 'fortex_alerts_total{type="INTRUSION",source="vision"} 1' in text
    assert "fortex_commands_total 2" in text          # alarme automatique : buzzer + LED
    assert "fortex_mosquitto_log_bytes 1234" in text
    assert "# TYPE fortex_last_reading_age_seconds gauge" in text


def test_dashboard_token_is_operator_only():
    sent = []
    service, _ = make(publish=lambda t, p: sent.append(t) or True)
    client = TestClient(create_app(service, api_token="ia-secret", dashboard_token="dash"))
    ia, dash = {"Authorization": "Bearer ia-secret"}, {"Authorization": "Bearer dash"}
    command = {"actuator": "buzzer", "state": True}
    assert client.post("/api/v1/commands", json=command).status_code == 401        # anonyme refuse
    assert client.post("/api/v1/commands", json=command, headers=dash).status_code == 200
    assert client.post("/api/v1/commands", json=command, headers=ia).status_code == 200
    assert client.post("/api/v1/alerts", json=INTRUSION, headers=dash).status_code == 401  # pas d'alerte
    assert client.post("/api/v1/alerts", json=INTRUSION, headers=ia).status_code == 201
    assert client.delete("/api/v1/people/x").status_code == 401
    assert client.delete("/api/v1/people/x", headers=dash).status_code == 404  # autorise, individu absent


def test_operator_required_for_sensitive_reads_and_actions():
    """OWASP A01 : donnees personnelles, acquittement et exercices reserves a l'operateur."""
    service, _ = make()
    client = TestClient(create_app(service, api_token="ia-secret", dashboard_token="dash"))
    dash = {"Authorization": "Bearer dash"}
    for method, url in [("get", "/api/v1/people"), ("get", "/api/v1/presence"),
                        ("post", "/api/v1/test/heat"), ("post", "/api/v1/alerts/1/ack")]:
        assert getattr(client, method)(url).status_code == 401, url
    assert client.post("/api/v1/test/heat", headers=dash).status_code == 201
    assert client.post("/api/v1/alerts/1/ack", headers=dash).status_code == 200
    # les lectures operationnelles restent ouvertes (ecran de supervision sans donnee personnelle)
    assert client.get("/api/v1/alerts").status_code == 200
    assert client.get("/health").status_code == 200


def test_security_headers_and_no_wildcard_cors():
    _, app = make()
    res = TestClient(app).get("/health", headers={"Origin": "http://evil.example"})
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Cache-Control"] == "no-store"
    assert "access-control-allow-origin" not in res.headers


def test_presence_only_to_authenticated_websocket():
    service, _ = make()
    app = create_app(service, api_token="ia-secret", dashboard_token="dash")
    ia = {"Authorization": "Bearer ia-secret"}
    with TestClient(app) as client, client.websocket_connect("/ws") as anon, client.websocket_connect("/ws") as op:
        op.send_json({"type": "auth", "token": "dash"})
        assert op.receive_json() == {"type": "auth", "ok": True}
        anon.send_json({"type": "auth", "token": "faux"})
        assert anon.receive_json() == {"type": "auth", "ok": False}
        anon.send_text("pas du json")  # ignore sans couper la connexion (OWASP A10)
        client.post("/api/v1/test/heat", headers=ia)
        assert anon.receive_json()["type"] == "alert" and op.receive_json()["type"] == "alert"
        service.hub.broadcast({"type": "presence", "kind": "entree", "person": "Alice"}, private=True)
        client.post("/api/v1/test/gas", headers=ia)
        assert op.receive_json()["type"] == "presence"
        assert anon.receive_json()["kind"] == "gas"  # l'anonyme recoit l'alerte suivante, pas la presence


def test_photo_size_is_bounded():
    service, _ = make()
    client = TestClient(create_app(service, dashboard_token="dash"))
    big = {"name": "X", "photo": "A" * 8_000_001}
    assert client.post("/api/v1/people", json=big, headers={"Authorization": "Bearer dash"}).status_code == 422
