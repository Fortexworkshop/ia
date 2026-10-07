import io

import cv2
import numpy as np
import pytest

flask = pytest.importorskip("flask")

from sentinel.admin import Analysis, FaceResult, create_app, decode_image, draw  # noqa: E402


def jpeg(width=200, height=150) -> bytes:
    return cv2.imencode(".jpg", np.full((height, width, 3), 128, np.uint8))[1].tobytes()


class FakeEngine:
    def __init__(self):
        self.db = {}

    def agents(self):
        return sorted(self.db)

    def enroll(self, name, images):
        files = [{"file": f, "ok": img is not None} for f, img in images]
        used = sum(f["ok"] for f in files)
        if used:
            self.db[name] = used
        return {"name": name, "enrolled": bool(used), "used": used, "files": files}

    def remove(self, name):
        return self.db.pop(name, None) is not None

    def analyze(self, image):
        return Analysis(faces=[FaceResult("Alice", 0.8, (10, 10, 40, 40))],
                        persons=[{"box": (0, 0, 100, 140), "confidence": 0.9, "authorized": "Alice"}],
                        image="data:image/jpeg;base64,xx")


@pytest.fixture
def client():
    return create_app(FakeEngine()).test_client()


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200 and b"Sentinel-X" in res.data


def test_enroll_list_and_delete(client):
    res = client.post("/api/agents", data={"name": "  Alice   Martin ", "photos": [(io.BytesIO(jpeg()), "a.jpg")]},
                      content_type="multipart/form-data")
    assert res.status_code == 201 and res.json["name"] == "Alice Martin"
    assert client.get("/api/agents").json == ["Alice Martin"]
    assert client.delete("/api/agents/Alice Martin").status_code == 204
    assert client.delete("/api/agents/Alice Martin").status_code == 404


def test_enroll_rejects_missing_name_or_unreadable_photo(client):
    assert client.post("/api/agents", data={"name": ""}, content_type="multipart/form-data").status_code == 400
    res = client.post("/api/agents", data={"name": "Bob", "photos": [(io.BytesIO(b"pas une image"), "x.jpg")]},
                      content_type="multipart/form-data")
    assert res.status_code == 422 and not res.json["enrolled"]


def test_analyze(client):
    res = client.post("/api/analyze", data={"image": (io.BytesIO(jpeg()), "t.jpg")}, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.json["intruders"] == 0 and res.json["faces"][0]["name"] == "Alice"
    assert client.post("/api/analyze", data={}, content_type="multipart/form-data").status_code == 400


def test_decode_image_downscales_large_photos():
    assert max(decode_image(jpeg(4000, 3000)).shape[:2]) == 1280
    assert decode_image(b"nope") is None


def test_draw_keeps_size():
    image = np.zeros((300, 400, 3), np.uint8)
    result = Analysis(faces=[FaceResult(None, 0.1, (10, 10, 50, 50))],
                      persons=[{"box": (0, 0, 200, 290), "confidence": 0.7, "authorized": None}])
    assert draw(image, result).shape == image.shape


# --- pointage : vraie logique (SQLite, regles), faux detecteurs ----------------
from presence.faces import FaceMatch  # noqa: E402
from presence.gestures import Gesture  # noqa: E402
from sentinel.admin import FaceEngine  # noqa: E402


class FakeRecognizer:
    def __init__(self):
        self.name = "Alice"

    def identify(self, image):
        return FaceMatch(self.name, 0.8, (10, 10, 40, 40)) if self.name != "-" else None


class FakeHands:
    def __init__(self):
        self.gesture = Gesture.NONE

    def detect(self, image):
        points = [(50.0 + i, 60.0 + i) for i in range(21)]
        return self.gesture, (points if self.gesture is not Gesture.NONE else None)


@pytest.fixture
def real_engine(tmp_path):
    engine = FaceEngine(tmp_path / "faces.npz", "", "", None, "", tmp_path / "presence.db")
    engine._recognizer, engine._hands = FakeRecognizer(), FakeHands()
    return engine


def checkin(client, engine, gesture, name="Alice"):
    engine._hands.gesture, engine._recognizer.name = gesture, name
    res = client.post("/api/checkin", data={"image": (io.BytesIO(jpeg()), "p.jpg")},
                      content_type="multipart/form-data")
    assert res.status_code == 200
    return res.json


def test_checkin_full_day(real_engine):
    client = create_app(real_engine).test_client()
    assert checkin(client, real_engine, Gesture.THUMB_UP)["events"] == ["ARRIVEE"]
    assert not checkin(client, real_engine, Gesture.THUMB_UP)["accepted"]  # pas de double arrivee
    assert checkin(client, real_engine, Gesture.THUMB_SIDE)["events"] == ["PAUSE_DEBUT"]
    assert checkin(client, real_engine, Gesture.THUMB_SIDE)["events"] == ["PAUSE_FIN"]
    assert checkin(client, real_engine, Gesture.THUMB_DOWN)["events"] == ["DEPART"]

    day = client.get("/api/attendance").json
    row = day["agents"][0]
    assert row["agent"] == "Alice" and row["pauses"] == 1 and row["status"] == "parti"
    assert row["arrival"] and row["departure"]
    csv_text = client.get("/api/attendance.csv").get_data(as_text=True)
    assert csv_text.startswith("agent;date;arrivee") and "Alice" in csv_text


def test_checkin_refusals(real_engine):
    client = create_app(real_engine).test_client()
    assert "Aucun visage" in checkin(client, real_engine, Gesture.THUMB_UP, name="-")["message"]
    assert "inconnu" in checkin(client, real_engine, Gesture.THUMB_UP, name=None)["message"]
    unread = checkin(client, real_engine, Gesture.NONE)
    assert not unread["accepted"] and "aucun geste" in unread["message"]
    assert client.get("/api/attendance").json["agents"] == []
    assert client.get("/api/attendance?day=pas-une-date").status_code == 400
