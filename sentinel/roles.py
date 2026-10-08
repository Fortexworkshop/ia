"""Roles des individus (page « Individus » du dashboard) pour les afficher sur le flux video.

Source : data/people.db, table `people` (backend/people.py). Relue regulierement, pour qu'un
role modifie dans le dashboard apparaisse sans redemarrer la vision.
"""

from __future__ import annotations

import sqlite3
import time
import unicodedata
from contextlib import closing
from pathlib import Path


def ascii_text(text: str) -> str:
    """OpenCV (putText) n'affiche pas les accents : « Sécurité » -> « Securite »."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


class RoleBook:
    def __init__(self, db_path: Path, refresh_seconds: float = 10.0):
        self.db_path = Path(db_path)
        self.refresh_seconds = refresh_seconds
        self._roles: dict[str, str] = {}
        self._loaded_at = float("-inf")

    def roles(self, now: float | None = None) -> dict[str, str]:
        now = time.monotonic() if now is None else now
        if now - self._loaded_at >= self.refresh_seconds:
            self._loaded_at = now
            self._roles = self._read()
        return self._roles

    def _read(self) -> dict[str, str]:
        if not self.db_path.exists():
            return {}
        try:
            with closing(sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)) as conn:
                return {name: role for name, role in conn.execute("SELECT name, role FROM people") if role}
        except sqlite3.Error:
            return self._roles  # base en cours d'ecriture : on garde la derniere lecture

    def label(self, name: str, now: float | None = None) -> str:
        """« Momo · Technicien » si un role est renseigne, sinon le nom seul (sans accents)."""
        role = self.roles(now).get(name, "")
        return ascii_text(f"{name} - {role}" if role else name)
