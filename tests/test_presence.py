"""Journal de presence : stockage SQLite, endpoints et client d'envoi."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from backend.presence import KINDS, PresenceLog


def test_add_and_recent_are_newest_first(tmp_path):
    log = PresenceLog(tmp_path / "presence_log.db")
    log.add("detection", "Kephren", ts="2026-10-07T12:00:00+02:00")
    log.add("entree", "Kephren", ts="2026-10-07T12:00:05+02:00")
    events = log.recent()
    assert [e["kind"] for e in events] == ["entree", "detection"]
    assert events[0]["id"] == 2 and events[0]["person"] == "Kephren"


def test_kinds_are_the_dashboard_contract():
    assert KINDS == ("detection", "entree", "pause", "reprise", "sortie")


def test_add_rejects_unknown_kind(tmp_path):
    log = PresenceLog(tmp_path / "presence_log.db")
    with pytest.raises(ValueError):
        log.add("inconnu")


def test_add_stamps_time_strips_person_and_limits(tmp_path):
    log = PresenceLog(tmp_path / "presence_log.db")
    event = log.add("sortie", "  Kephren  ")
    assert event["ts"] and event["person"] == "Kephren"
    for _ in range(5):
        log.add("detection")
    assert len(log.recent(limit=2)) == 2


def test_endpoints_record_and_list(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    log = PresenceLog(tmp_path / "presence_log.db")
    service = Service(MemoryStore(), Hub(), None, node_id="SX-01")
    client = TestClient(create_app(service, api_token="s3cret", presence=log))
    auth = {"Authorization": "Bearer s3cret"}

    assert client.get("/api/v1/presence").status_code == 401  # donnees personnelles : operateur seulement
    assert client.get("/api/v1/presence", headers=auth).json() == []
    assert client.post("/api/v1/presence", json={"kind": "detection"}).status_code == 401
    assert client.post("/api/v1/presence", json={"kind": "inconnu"}, headers=auth).status_code == 422

    created = client.post("/api/v1/presence", json={"kind": "entree", "person": "Kephren"}, headers=auth)
    assert created.status_code == 201 and created.json()["kind"] == "entree"
    events = client.get("/api/v1/presence?limit=10", headers=auth).json()
    assert events[0]["person"] == "Kephren" and events[0]["id"] == created.json()["id"]


def test_presence_without_log_is_empty_and_read_only():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    client = TestClient(create_app(Service(MemoryStore(), Hub(), None, node_id="SX-01")))
    assert client.get("/api/v1/presence").json() == []  # aucun jeton configure : lecture libre (developpement)
    assert client.post("/api/v1/presence", json={"kind": "detection"}).status_code == 503


@pytest.fixture
def api():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append((self.path, json.loads(body)))
            self.send_response(201)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}", received
    server.shutdown()


def test_presence_client_posts_to_its_own_endpoint(api):
    from sentinel.alerts import PresenceClient, build_presence

    url, received = api
    client = PresenceClient(url)
    client.send(build_presence("SX-01", "entree", "Kephren"))
    client.flush()
    assert client.sent == 1
    path, body = received[0]
    assert path == "/api/v1/presence"
    assert body["kind"] == "entree" and body["person"] == "Kephren"
    assert body["message"] == "Entree (pouce en haut)"


def test_presence_client_offline_only_prints(capsys):
    from sentinel.alerts import PresenceClient, build_presence

    client = PresenceClient("")
    client.send(build_presence("SX-01", "detection", "Kephren"))
    assert "Une personne se presente" in capsys.readouterr().out
    assert client.sent == 0
