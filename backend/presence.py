"""Journal de presence : detections de la vision et pointage par geste.

`kind` vaut :
  - "detection" : une personne se presente devant la camera (vision) ;
  - "entree"    : pouce en haut, valide par la personne reconnue ;
  - "pause"     : pouce de cote, debut de pause ;
  - "reprise"   : pouce de cote, retour de pause ;
  - "sortie"    : pouce en bas.

Les evenements sont horodates et diffuses au dashboard par WebSocket (`type: "presence"`).
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from datetime import datetime
from pathlib import Path

KINDS = ("detection", "entree", "pause", "reprise", "sortie")

SCHEMA = """
CREATE TABLE IF NOT EXISTS presence_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    person TEXT NOT NULL DEFAULT ''
)
"""


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class PresenceLog:
    """Evenements de presence, du plus recent au plus ancien."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        # Une connexion par appel : sqlite3 interdit de partager une connexion entre threads.
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, kind: str, person: str = "", ts: str = "") -> dict:
        kind = kind.strip().lower()
        if kind not in KINDS:
            raise ValueError(f"kind inconnu : {kind!r} (attendu : {', '.join(KINDS)})")
        event = {"ts": ts.strip() or _now(), "kind": kind, "person": person.strip()}
        with self.lock, closing(self._connect()) as conn:
            cursor = conn.execute("INSERT INTO presence_events (ts, kind, person) VALUES (?, ?, ?)",
                                  (event["ts"], event["kind"], event["person"]))
            conn.commit()
            event["id"] = cursor.lastrowid
        return event

    def recent(self, limit: int = 50) -> list[dict]:
        with self.lock, closing(self._connect()) as conn:
            rows = conn.execute("SELECT id, ts, kind, person FROM presence_events ORDER BY id DESC LIMIT ?",
                                (max(1, min(limit, 500)),)).fetchall()
        return [dict(row) for row in rows]
