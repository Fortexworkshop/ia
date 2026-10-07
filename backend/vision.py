"""Pilotage du processus de vision depuis le dashboard (bouton Arreter / Demarrer).

La webcam est un peripherique **exclusif** : pendant que `sentinel_vision.py` tourne, aucune autre
application ne peut ouvrir `/dev/video0`. Arreter la vision libere la camera, la demarrer la reprend.
Le script est lance avec l'interpreteur courant, dans la racine du depot, et sa sortie est ecrite
dans `data/vision.log` (les alertes et pointages y restent lisibles).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

VISION_SCRIPT = Path("scripts") / "sentinel_vision.py"


class VisionController:
    """Demarre et arrete le script de vision. Sans effet si le backend n'a pas les modules."""

    def __init__(self, root: Path, port: int = 8081, api_url: str = "", api_token: str = "",
                 pointage: bool = True, log_path: Path | None = None):
        self.root = Path(root)
        self.port = port
        self.api_url = api_url
        self.api_token = api_token
        self.pointage = pointage
        self.log_path = Path(log_path) if log_path else None
        self.lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._log = None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def status(self) -> dict:
        return {"running": self.running, "available": True, "port": self.port,
                "pid": self._process.pid if self.running else None,
                "pointage": self.pointage}

    def start(self) -> dict:
        with self.lock:
            if self.running:
                return self.status()
            command = [sys.executable, "-u", str(self.root / VISION_SCRIPT), "--no-window",
                       "--port", str(self.port)]
            if self.pointage:
                command.append("--pointage")
            env = {**os.environ, "SENTINEL_API_URL": self.api_url or f"http://localhost:8080"}
            if self.api_token:
                env["SENTINEL_API_TOKEN"] = self.api_token
            stdout = None
            if self.log_path:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                self._log = self.log_path.open("a", encoding="utf-8")
                stdout = self._log
            self._process = subprocess.Popen(command, cwd=str(self.root), env=env,
                                             stdout=stdout, stderr=subprocess.STDOUT)
        return self.status()

    def stop(self) -> dict:
        with self.lock:
            process, self._process = self._process, None
            log, self._log = self._log, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if log is not None:
            log.close()
        return self.status()
