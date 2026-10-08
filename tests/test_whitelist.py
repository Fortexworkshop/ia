import os
import time

import numpy as np

from presence.faces import FaceDatabase
from sentinel.whitelist import LiveWhitelist


class FakeRecognizer:
    def __init__(self, db):
        self.db = db


def save(path, names):
    db = FaceDatabase(path)
    db.embeddings = {}
    rng = np.random.default_rng(0)
    for name in names:
        db.add(name, [rng.normal(size=128)])
    db.save()
    # garantit une date de modification differente meme si deux ecritures sont tres proches
    stamp = time.time() + len(names)
    os.utime(path, (stamp, stamp))


def test_deleted_person_is_forgotten_without_restart(tmp_path):
    path = tmp_path / "faces.npz"
    save(path, ["Momo", "ismo"])
    recognizer = FakeRecognizer(FaceDatabase(path))
    live = LiveWhitelist(recognizer, path, check_seconds=2)
    assert live.refresh(now=0) is None                  # fichier inchange

    save(path, ["Momo"])                                # suppression depuis le dashboard
    assert live.refresh(now=1) is None                  # controle toutes les 2 s seulement
    assert live.refresh(now=3) == ["Momo"]
    assert "ismo" not in recognizer.db.embeddings       # n'est plus reconnu

    save(path, ["Momo", "Nouvel agent"])                # ajout
    assert live.refresh(now=6) == ["Momo", "Nouvel agent"]


def test_file_deleted_means_empty_list(tmp_path):
    path = tmp_path / "faces.npz"
    save(path, ["Momo"])
    recognizer = FakeRecognizer(FaceDatabase(path))
    live = LiveWhitelist(recognizer, path)
    path.unlink()
    assert live.refresh(now=10) == []
    assert recognizer.db.embeddings == {}
