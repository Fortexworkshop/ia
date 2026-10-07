"""Envoi des alertes IA vers l'API du PC Serveur Local : POST /api/v1/alerts (JSON).

Format par defaut (a ajuster avec l'equipe DEV) :

{
  "node_id":   "SENTINEL-X-01",
  "source":    "vision" | "anomaly",
  "type":      "INTRUSION" | "ENV_ANOMALY",
  "severity":  "info" | "warning" | "critical",
  "message":   "Presence humaine detectee (2 personnes)",
  "timestamp": "2026-10-06T14:32:05+02:00",
  "data":      { ... details propres a la source ... }
}

L'envoi se fait dans un thread pour ne jamais bloquer la boucle video.
Sans SENTINEL_API_URL, les alertes sont seulement affichees (mode hors ligne).

PresenceClient (meme mecanique) envoie le journal de presence vers POST /api/v1/presence :
`{"node_id", "kind", "person", "message", "timestamp"}` avec `kind` : "detection" (une personne
se presente), "entree" (pouce en haut), "pause" / "reprise" (pouce de cote), "sortie" (pouce en bas).
"""

from __future__ import annotations

import json
import queue
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime
from enum import Enum

ALERTS_PATH = "/api/v1/alerts"
PRESENCE_PATH = "/api/v1/presence"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def build_alert(node_id: str, source: str, alert_type: str, severity: Severity, message: str,
                data: dict | None = None, when: datetime | None = None) -> dict:
    when = when or datetime.now().astimezone()
    return {
        "node_id": node_id,
        "source": source,
        "type": alert_type,
        "severity": Severity(severity).value,
        "message": message,
        "timestamp": when.isoformat(timespec="seconds"),
        "data": data or {},
    }


class AlertClient:
    def __init__(self, base_url: str = "", token: str = "", ca_cert: str = "",
                 timeout: float = 3.0, retries: int = 2, path: str = ALERTS_PATH,
                 label: str = "ALERTE"):
        self.url = base_url.rstrip("/") + path if base_url else ""
        self.token = token
        self.timeout = timeout
        self.retries = retries
        self.label = label
        self.context = ssl.create_default_context(cafile=ca_cert) if ca_cert else None
        self.sent = 0
        self.failed = 0
        self._queue: queue.Queue[dict | None] = queue.Queue(maxsize=100)
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def send(self, alert: dict) -> None:
        """Non bloquant : si la file est pleine (API tombee), l'alerte la plus ancienne est perdue."""
        print(f"[{self.label}] {alert['severity'].upper()} {alert['type']} : {alert['message']}")
        self._enqueue(alert)

    def _enqueue(self, payload: dict) -> None:
        """Non bloquant : si la file est pleine (API tombee), le message le plus ancien est perdu."""
        if not self.url:
            return
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            self._queue.get_nowait()
            self._queue.task_done()
            self.failed += 1
            self._queue.put_nowait(payload)

    def post(self, alert: dict) -> bool:
        """Envoi synchrone avec quelques tentatives. Renvoie True si l'API a accepte (2xx)."""
        body = json.dumps(alert).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for _ in range(self.retries + 1):
            request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout, context=self.context) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except (urllib.error.URLError, OSError) as exc:
                print(f"[!] API injoignable ({exc})")
        return False

    def _worker(self) -> None:
        while True:
            alert = self._queue.get()
            if alert is None:
                return
            if self.post(alert):
                self.sent += 1
            else:
                self.failed += 1
            self._queue.task_done()

    def flush(self, timeout: float = 5.0) -> None:
        """Attend l'envoi des alertes en file (utile en fin de script et dans les tests)."""
        done = threading.Event()
        threading.Thread(target=lambda: (self._queue.join(), done.set()), daemon=True).start()
        done.wait(timeout)


def build_presence(node_id: str, kind: str, person: str = "", message: str = "",
                   when: datetime | None = None) -> dict:
    """Evenement de presence : `kind` vaut "detection", "entree" ou "sortie"."""
    when = when or datetime.now().astimezone()
    return {
        "node_id": node_id,
        "kind": kind,
        "person": person,
        "message": message or {"detection": "Une personne se presente",
                               "entree": "Entree (pouce en haut)",
                               "pause": "Pause (pouce de cote)",
                               "reprise": "Reprise apres pause (pouce de cote)",
                               "sortie": "Sortie (pouce en bas)"}.get(kind, kind),
        "timestamp": when.isoformat(timespec="seconds"),
    }


class PresenceClient(AlertClient):
    """Journal de presence de la vision : POST /api/v1/presence (meme file d'attente et TLS)."""

    def __init__(self, base_url: str = "", token: str = "", ca_cert: str = "",
                 timeout: float = 3.0, retries: int = 2):
        super().__init__(base_url, token, ca_cert, timeout, retries,
                         path=PRESENCE_PATH, label="PRESENCE")

    def send(self, event: dict) -> None:
        who = event.get("person") or "personne inconnue"
        print(f"[{self.label}] {event['message']} : {who}")
        self._enqueue(event)
