"""Liste blanche des individus : donnees SQLite, empreintes (simulees) et endpoints.

Le FaceEnroller reel utilise OpenCV : il est remplace ici par un double, et son repli
sans OpenCV est teste a part (FaceEnroller.error).
"""

import base64

import numpy as np
import pytest

from backend.people import FaceEnroller, PeopleStore, decode_photo

JPEG = b"\xff\xd8\xff" + b"photo" * 10


class FakeEnroller:
    """Double du FaceEnroller : aucune image n'est analysee."""

    def __init__(self, known=()):
        self.embeddings = {name: np.ones(128) for name in known}
        self.error = None

    def enrolled(self):
        return set(self.embeddings)

    def enroll(self, name, photo):
        if photo == b"pas un visage":
            return False
        self.embeddings[name] = np.ones(128)
        return True

    def rename(self, old, new):
        if old not in self.embeddings:
            return False
        self.embeddings[new] = self.embeddings.pop(old)
        return True

    def forget(self, name):
        return self.embeddings.pop(name, None) is not None


def make(tmp_path, known=()):
    enroller = FakeEnroller(known)
    return PeopleStore(tmp_path / "people.db", enroller), enroller


def test_decode_photo_accepts_data_url_and_raw_base64():
    encoded = base64.b64encode(JPEG).decode()
    assert decode_photo("data:image/jpeg;base64," + encoded) == JPEG
    assert decode_photo(encoded) == JPEG
    assert decode_photo("data:image/png;base64,@@pas-du-base64@@") is None
    assert decode_photo("") is None


def test_save_lists_and_deletes(tmp_path):
    store, _ = make(tmp_path)
    result = store.save("  Alice Martin  ", "  Superviseure ", "  RAS  ")
    assert result["face_error"] is None and result["person"]["name"] == "Alice Martin"
    assert result["person"]["role"] == "Superviseure" and result["person"]["notes"] == "RAS"
    assert result["person"]["face"] is False

    assert [p["name"] for p in store.list()] == ["Alice Martin"]
    assert store.delete("Alice Martin") and store.list() == []
    assert store.delete("Personne inconnue") is False


def test_save_rejects_empty_name(tmp_path):
    store, _ = make(tmp_path)
    with pytest.raises(ValueError):
        store.save("   ")


def test_photo_is_stored_as_embedding_and_bad_photo_reported(tmp_path):
    store, enroller = make(tmp_path)
    result = store.save("Alice", photo="data:image/jpeg;base64," + base64.b64encode(JPEG).decode())
    assert result["face_error"] is None and result["person"]["face"] is True
    assert "Alice" in enroller.embeddings

    bad = store.save("Bob", photo="data:image/jpeg;base64," + base64.b64encode(b"pas un visage").decode())
    assert bad["person"]["face"] is False and "aucun visage" in bad["face_error"]

    broken = store.save("Chloe", photo="pas-du-base64")
    assert broken["face_error"].startswith("photo illisible")


def test_rename_moves_the_face_embedding(tmp_path):
    store, enroller = make(tmp_path, known=["Alice"])
    result = store.save("Alicia", previous="Alice")
    assert result["person"]["name"] == "Alicia" and result["person"]["face"] is True
    assert enroller.embeddings.keys() == {"Alicia"}
    assert [p["name"] for p in store.list()] == ["Alicia"]


def test_list_includes_faces_enrolled_in_command_line(tmp_path):
    store, _ = make(tmp_path, known=["Kephren"])
    assert store.list() == [{"name": "Kephren", "role": "", "notes": "", "face": True,
                             "created_at": "", "updated_at": ""}]


def test_face_enroller_reports_missing_models(tmp_path):
    enroller = FaceEnroller(tmp_path / "faces.npz", tmp_path / "absent.onnx", tmp_path / "absent.onnx")
    assert enroller.enrolled() == set()
    assert "modeles de vision absents" in enroller.error
    assert enroller.enroll("Alice", JPEG) is False


def test_endpoints_require_token_and_manage_people(tmp_path):
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    store, _ = make(tmp_path)
    service = Service(MemoryStore(), Hub(), None, node_id="SX-01")
    client = TestClient(create_app(service, api_token="s3cret", people=store))
    auth = {"Authorization": "Bearer s3cret"}

    assert client.get("/api/v1/people").json() == []
    assert client.post("/api/v1/people", json={"name": "Alice"}).status_code == 401
    assert client.post("/api/v1/people", json={"name": "  "}, headers=auth).status_code == 400

    created = client.post("/api/v1/people", json={"name": "Alice", "role": "Superviseure"}, headers=auth)
    assert created.status_code == 201 and created.json()["person"]["face"] is False
    assert [p["name"] for p in client.get("/api/v1/people").json()] == ["Alice"]

    assert client.delete("/api/v1/people/Alice").status_code == 401
    assert client.delete("/api/v1/people/Pas%20la", headers=auth).status_code == 404
    assert client.delete("/api/v1/people/Alice", headers=auth).json() == {"deleted": "Alice"}
    assert client.get("/api/v1/people").json() == []


def test_endpoints_without_people_store_are_empty_and_read_only():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient  # noqa: E402

    from backend.app import Hub, Service, create_app  # noqa: E402
    from backend.store import MemoryStore  # noqa: E402

    app = create_app(Service(MemoryStore(), Hub(), None, node_id="SX-01"))
    client = TestClient(app)
    assert client.get("/api/v1/people").json() == []
    assert client.post("/api/v1/people", json={"name": "Alice"}).status_code == 503
