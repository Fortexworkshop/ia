"""Liste blanche des visages, rechargee a chaud.

La page « Individus » du dashboard (backend/people.py) ajoute ou supprime des empreintes dans
data/faces.npz pendant que la vision tourne. On surveille la date de modification du fichier :
une personne supprimee cesse d'etre reconnue en ~2 s, sans redemarrer la vision.
"""

from __future__ import annotations

from pathlib import Path


class LiveWhitelist:
    def __init__(self, recognizer, path: Path, check_seconds: float = 2.0):
        self.recognizer = recognizer          # presence.faces.FaceRecognizer (attribut .db remplace)
        self.path = Path(path)
        self.check_seconds = check_seconds
        self._checked_at = float("-inf")
        self._signature = self._stat()

    def _stat(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except FileNotFoundError:
            return None

    def names(self) -> list[str]:
        return sorted(self.recognizer.db.embeddings)

    def refresh(self, now: float) -> list[str] | None:
        """Recharge si le fichier a change. Renvoie la nouvelle liste de noms, ou None si inchange."""
        if now - self._checked_at < self.check_seconds:
            return None
        self._checked_at = now
        signature = self._stat()
        if signature == self._signature:
            return None
        from presence.faces import FaceDatabase

        try:
            database = FaceDatabase(self.path)  # fichier absent = liste vide
        except Exception:
            return None  # ecriture en cours : on reessaiera au prochain controle
        self._signature = signature
        self.recognizer.db = database
        return self.names()
