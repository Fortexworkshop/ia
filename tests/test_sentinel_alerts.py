import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from sentinel.alerts import AlertClient, Severity, build_alert


def test_build_alert_format():
    when = datetime(2026, 10, 6, 14, 32, 5, tzinfo=timezone.utc)
    alert = build_alert("SX-01", "vision", "INTRUSION", Severity.CRITICAL, "intrus", {"persons": 1}, when)
    assert alert == {
        "node_id": "SX-01", "source": "vision", "type": "INTRUSION", "severity": "critical",
        "message": "intrus", "timestamp": "2026-10-06T14:32:05+00:00", "data": {"persons": 1},
    }
    json.dumps(alert)  # serialisable


@pytest.fixture
def api():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, self.headers.get("Authorization"), json.loads(body)))
            self.send_response(201)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", received
    server.shutdown()


def test_client_posts_to_alerts_endpoint(api):
    url, received = api
    client = AlertClient(url + "/", token="secret")
    client.send(build_alert("SX-01", "anomaly", "ENV_ANOMALY", Severity.WARNING, "derive"))
    client.flush()
    assert client.sent == 1
    path, auth, body = received[0]
    assert path == "/api/v1/alerts"
    assert auth == "Bearer secret"
    assert body["type"] == "ENV_ANOMALY"


def test_unreachable_api_does_not_raise():
    client = AlertClient("http://127.0.0.1:9", timeout=0.2, retries=0)
    client.send(build_alert("SX-01", "vision", "INTRUSION", Severity.CRITICAL, "x"))
    client.flush()
    assert client.failed == 1


def test_offline_mode_only_prints(capsys):
    client = AlertClient("")
    client.send(build_alert("SX-01", "vision", "INTRUSION", Severity.CRITICAL, "intrus"))
    assert "INTRUSION" in capsys.readouterr().out
