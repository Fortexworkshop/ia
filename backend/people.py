"""Individus de la liste blanche : donnees (SQLite) et empreintes faciales (data/faces.npz).

Les empreintes sont ecrites dans le **meme fichier** que celui lu par la vision
(`sentinel_vision.py --whitelist`) et par la plateforme d'administration : un individu ajoute
depuis le dashboard est donc directement reconnu par l'IA de vision.

OpenCV n'est pas une dependance du conteneur backend : l'empreinte est calculee quand les
modules de vision sont disponibles (execution sur la machine du PC serveur, la ou vit la
webcam), sinon l'individu est quand meme enregistre et `face_error` explique pourquoi.
"""

from __future__ import annotations

import base64
import binascii
import re
import sqlite3
import threading
from contextlib import closing
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_DATA_URL = re.compile(r"^data:image/[a-zA-Z0-9.+-]+;base64,")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def decode_photo(photo: str) -> bytes | None:
    """Photo du navigateur : data URL (`data:image/jpeg;base64,…`) ou base64 brut."""
    payload = _DATA_URL.sub("", photo.strip())
    if not payload:
        return None
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None


class FaceEnroller:
    """Empreinte faciale d'une photo (YuNet + SFace), si les modules de vision sont installes."""

    def __init__(self, faces_db_path: Path, detector_model: Path, recognizer_model: Path):
        self.faces_db_path = Path(faces_db_path)
        self.detector_model = Path(detector_model)
        self.recognizer_model = Path(recognizer_model)
        self._db = None
        self._recognizer = None
        self._lock = threading.Lock()
        self._error: str | None = None

    def _load(self) -> None:
        if self._db is not None or self._error is not None:
            return
        try:
            from presence.faces import FaceDatabase, FaceRecognizer
        except ImportError as exc:
            self._error = f"modules de vision absents du backend ({exc.name})"
            return
        missing = [p.name for p in (self.detector_model, self.recognizer_model) if not p.exists()]
        if missing:
            self._error = f"modeles de vision absents ({', '.join(missing)}) : lance scripts/download_models.py"
            return
        self._db = FaceDatabase(self.faces_db_path)
        self._recognizer = FaceRecognizer(str(self.detector_model), str(self.recognizer_model), self._db)

    @property
    def error(self) -> str | None:
        self._load()
        return self._error

    def enrolled(self) -> set[str]:
        self._load()
        return set(self._db.embeddings) if self._db is not None else set()

    def enroll(self, name: str, photo: bytes) -> bool:
        """Ajoute ou remplace l'empreinte de `name`. False si aucun visage exploitable."""
        self._load()
        if self._recognizer is None:
            return False
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return False
        with self._lock:
            face = self._recognizer.largest_face(image)
            if face is None:
                return False
            self._db.add(name, [self._recognizer.embedding(image, face)])
            self._db.save()
        return True

    def rename(self, old: str, new: str) -> bool:
        """Deplace l'empreinte d'un individu (le nom est la cle du fichier .npz)."""
        self._load()
        if self._db is None or old not in self._db.embeddings:
            return False
        with self._lock:
            embedding = self._db.embeddings.pop(old)
            self._db.add(new, [embedding])
            self._db.save()
        return True

    def forget(self, name: str) -> bool:
        self._load()
        if self._db is None:
            return False
        with self._lock:
            removed = self._db.remove(name)
            if removed:
                self._db.save()
        return removed


class PeopleStore:
    """Individus de la liste blanche. Le nom identifie l'individu (cle de data/faces.npz)."""

    def __init__(self, db_path: Path, enroller: FaceEnroller):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enroller = enroller
        self.lock = threading.Lock()
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        # Une connexion par appel : sqlite3 interdit de partager une connexion entre threads.
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _person(name: str, role: str = "", notes: str = "", face: bool = False,
                created_at: str = "", updated_at: str = "") -> dict:
        return {"name": name, "role": role, "notes": notes, "face": face,
                "created_at": created_at, "updated_at": updated_at}

    def list(self) -> list[dict]:
        """Individus declares dans le dashboard **et** empreintes enregistrees en ligne de commande."""
        faces = self.enroller.enrolled()
        with self.lock, closing(self._connect()) as conn:
            rows = {row["name"]: row for row in conn.execute("SELECT * FROM people")}

        def person(name: str, row: sqlite3.Row | None) -> dict:
            if row is None:  # empreinte seule, ajoutee par scripts/enroll.py
                return self._person(name, face=True)
            return self._person(row["name"], row["role"], row["notes"], row["name"] in faces,
                                row["created_at"], row["updated_at"])

        return sorted((person(name, rows.get(name)) for name in set(rows) | faces),
                      key=lambda p: p["name"].lower())

    def save(self, name: str, role: str = "", notes: str = "", photo: str = "",
             previous: str = "") -> dict:
        """Cree ou met a jour un individu. `previous` = ancien nom, si renomme."""
        name, old = name.strip(), (previous or name).strip()
        if not name:
            raise ValueError("le nom est obligatoire")
        role, notes = role.strip(), notes.strip()

        with self.lock, closing(self._connect()) as conn:
            existing = conn.execute("SELECT * FROM people WHERE name = ?", (old,)).fetchone()
            created_at = existing["created_at"] if existing else _now()
            if existing and old != name:
                conn.execute("DELETE FROM people WHERE name = ?", (old,))
            conn.execute(
                """INSERT INTO people (name, role, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET role = excluded.role, notes = excluded.notes,
                                                   updated_at = excluded.updated_at""",
                (name, role, notes, created_at, _now()),
            )
            conn.commit()

        if old != name and old in self.enroller.enrolled():
            self.enroller.rename(old, name)
        enrolled = name in self.enroller.enrolled()
        face_error = None
        if photo:
            raw = decode_photo(photo)
            if raw is None:
                face_error = "photo illisible (base64 attendu)"
            elif self.enroller.enroll(name, raw):
                enrolled = True
            else:
                face_error = self.enroller.error or "aucun visage detectable sur la photo"

        return {"person": self._person(name, role, notes, enrolled, created_at, _now()),
                "face_error": face_error}

    def delete(self, name: str) -> bool:
        """Droit a l'effacement : retire les donnees et l'empreinte faciale."""
        with self.lock, closing(self._connect()) as conn:
            removed = conn.execute("DELETE FROM people WHERE name = ?", (name,)).rowcount > 0
            conn.commit()
        forgotten = self.enroller.forget(name)
        return removed or forgotten
