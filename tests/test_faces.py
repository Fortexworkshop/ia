import numpy as np

from presence.faces import FaceDatabase


def test_match_known_and_reject_unknown(tmp_path):
    rng = np.random.default_rng(0)
    alice, bob = rng.normal(size=128), rng.normal(size=128)
    db = FaceDatabase(tmp_path / "faces.npz")
    db.add("alice", [alice + rng.normal(scale=0.1, size=128) for _ in range(3)])
    db.add("bob", [bob])
    db.save()

    reloaded = FaceDatabase(tmp_path / "faces.npz")
    assert reloaded.best_match(alice)[0] == "alice"
    assert reloaded.best_match(bob)[0] == "bob"
    assert reloaded.best_match(rng.normal(size=128))[0] is None


def test_empty_database():
    assert FaceDatabase("/nonexistent/faces.npz").best_match(np.ones(128)) == (None, 0.0)
