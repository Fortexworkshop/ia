"""Pilotage du processus de vision : demarrage, arret et endpoints.

Le script reel est remplace par un script factice qui attend, pour ne pas ouvrir la webcam.
"""

import subprocess
import sys

import pytest

from backend.vision import VisionController

FAKE = "import time\nprint('vision factice', flush=True)\ntime.sleep(60)\n"


@pytest.fixture
def root(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "sentinel_vision.py").write_text(FAKE, encoding="utf-8")
    return tmp_path


def controller(root, tmp_path, **kwargs):
    return VisionController(root, log_path=tmp_path / "vision.log", **kwargs)


def test_start_then_stop_manages_the_process(root, tmp_path):
    vision = controller(root, tmp_path)
    assert vision.status()["running"] is False and vision.status()["available"] is True

    started = vision.start()
    assert started["running"] is True and started["pid"]
    assert vision.running is True

    stopped = vision.stop()
    assert stopped["running"] is False and stopped["pid"] is None


def test_start_is_idempotent_and_stop_without_start_is_harmless(root, tmp_path):
    vision = controller(root, tmp_path)
    assert vision.stop()["running"] is False
    assert vision.start()["pid"] == vision.start()["pid"]  # le 2e start ne relance pas
    vision.stop()


def spy_on_popen(monkeypatch, recorded):
    """Intercepte Popen en gardant le vrai, pour ne pas se rappeler soi-meme."""
    real_popen = subprocess.Popen

    def fake_popen(command, **kwargs):
        recorded["command"] = command
        recorded["env"] = kwargs.get("env", {})
        return real_popen([sys.executable, "-c", "import time; time.sleep(30)"])

    monkeypatch.setattr("backend.vision.subprocess.Popen", fake_popen)


def test_command_and_environment(root, tmp_path, monkeypatch):
    recorded = {}
    spy_on_popen(monkeypatch, recorded)
    vision = VisionController(root, port=9090, api_url="http://localhost:8080", api_token="s3cret",
                             log_path=tmp_path / "vision.log")
    vision.start()
    vision.stop()

    command = recorded["command"]
    assert "--no-window" in command and "--pointage" in command
    assert command[command.index("--port") + 1] == "9090"
    assert recorded["env"]["SENTINEL_API_URL"] == "http://localhost:8080"
    assert recorded["env"]["SENTINEL_API_TOKEN"] == "s3cret"


def test_pointage_can_be_disabled(root, tmp_path, monkeypatch):
    recorded = {}
    spy_on_popen(monkeypatch, recorded)
    vision = VisionController(root, pointage=False, log_path=tmp_path / "vision.log")
    vision.start()
    vision.stop()
    assert "--pointage" not in recorded["command"]


def test_endpoints_drive_the_controller(root, tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    vision = controller(root, tmp_path)
    client = TestClient(create_app(Service(MemoryStore(), Hub(), None, node_id="SX-01"),
                                   api_token="s3cret", vision=vision))
    auth = {"Authorization": "Bearer s3cret"}

    assert client.get("/api/v1/vision").json()["running"] is False
    assert client.post("/api/v1/vision/start").status_code == 401
    assert client.post("/api/v1/vision/start", headers=auth).json()["running"] is True
    assert client.get("/api/v1/vision").json()["running"] is True
    assert client.post("/api/v1/vision/stop", headers=auth).json()["running"] is False


def test_vision_without_controller_is_reported_unavailable():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    client = TestClient(create_app(Service(MemoryStore(), Hub(), None, node_id="SX-01")))
    assert client.get("/api/v1/vision").json() == {"running": False, "available": False}
    assert client.post("/api/v1/vision/start").status_code == 503
