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
    assert client.post(f"/api/v1/alerts/{res.json()['id']}/ack").json()["acknowledged"]
    assert client.post("/api/v1/alerts/999/ack").status_code == 404


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
