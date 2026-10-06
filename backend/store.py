"""Stockage : PostgreSQL (schema du depot infra) ou memoire (tests / base indisponible).

Tables utilisees (infra/postgres/init/01-init.sql) :
  mesures_capteurs(temperature_c, humidite_pct, niveau_gaz, presence_detectee, date_mesure)
  alertes(type_alerte, gravite, message, date_creation, acquittee)
  statut_boitier(nom_boitier, statut, wifi_connecte, adresse_ip, date_mise_a_jour)
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime


class MemoryStore:
    def __init__(self, limit: int = 500):
        self.readings: deque[dict] = deque(maxlen=limit)
        self.alerts: deque[dict] = deque(maxlen=limit)
        self.status: dict[str, dict] = {}
        self._next_id = 1
        self.backend = "memoire"

    def add_reading(self, node: str, reading: dict) -> datetime:
        when = datetime.now().astimezone()
        self.readings.append({**reading, "node_id": node, "ts": when})
        return when

    def add_alert(self, alert: dict) -> int:
        alert_id, self._next_id = self._next_id, self._next_id + 1
        self.alerts.append({**alert, "id": alert_id, "acknowledged": False})
        return alert_id

    def acknowledge(self, alert_id: int) -> bool:
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False

    def touch_status(self, node: str, ip: str | None = None) -> None:
        self.status[node] = {"node_id": node, "statut": "en_ligne", "wifi": True, "ip": ip,
                             "updated": datetime.now().astimezone().isoformat(timespec="seconds")}

    def recent_readings(self, limit: int) -> list[dict]:
        return list(self.readings)[-limit:]

    def recent_alerts(self, limit: int) -> list[dict]:
        return list(reversed(self.alerts))[:limit]

    def devices(self) -> list[dict]:
        return list(self.status.values())

    def healthy(self) -> bool:
        return True


class PostgresStore:
    """Une connexion partagee, protegee par un verrou, reconnectee si la base redemarre."""

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        import psycopg

        self._psycopg = psycopg
        self._dsn = dict(host=host, port=port, dbname=dbname, user=user, password=password, connect_timeout=3)
        self._lock = threading.Lock()
        self._conn = None
        self.backend = f"postgresql://{user}@{host}:{port}/{dbname}"
        self._connect()

    def _connect(self):
        self._conn = self._psycopg.connect(**self._dsn, autocommit=True)

    def _run(self, sql: str, params=(), fetch: bool = False):
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._conn is None or self._conn.closed:
                        self._connect()
                    with self._conn.cursor() as cur:
                        cur.execute(sql, params)
                        return cur.fetchall() if fetch else (cur.fetchone() if cur.description else None)
                except self._psycopg.OperationalError:
                    self._conn = None
                    if attempt == 2:
                        raise

    def add_reading(self, node: str, reading: dict) -> datetime:
        row = self._run(
            "INSERT INTO mesures_capteurs (temperature_c, humidite_pct, niveau_gaz, presence_detectee) "
            "VALUES (%s, %s, %s, %s) RETURNING date_mesure",
            (reading["temperature"], reading["humidity"], reading["gas"], bool(reading["pir"])))
        return row[0]

    def add_alert(self, alert: dict) -> int:
        source = alert.get("source") or "?"
        row = self._run(
            "INSERT INTO alertes (type_alerte, gravite, message) VALUES (%s, %s, %s) RETURNING id",
            (str(alert.get("type", "ALERTE"))[:50], str(alert.get("severity", "warning"))[:20],
             f"[{source}] {alert.get('message', '')}"))
        return row[0]

    def acknowledge(self, alert_id: int) -> bool:
        row = self._run("UPDATE alertes SET acquittee = TRUE WHERE id = %s RETURNING id", (alert_id,))
        return row is not None

    def touch_status(self, node: str, ip: str | None = None) -> None:
        row = self._run(
            "UPDATE statut_boitier SET statut = 'en_ligne', wifi_connecte = TRUE, "
            "adresse_ip = COALESCE(%s::inet, adresse_ip), date_mise_a_jour = NOW() "
            "WHERE nom_boitier = %s RETURNING id", (ip, node))
        if row is None:
            self._run("INSERT INTO statut_boitier (nom_boitier, statut, wifi_connecte, adresse_ip) "
                      "VALUES (%s, 'en_ligne', TRUE, %s::inet)", (node, ip))

    def recent_readings(self, limit: int) -> list[dict]:
        rows = self._run(
            "SELECT temperature_c, humidite_pct, niveau_gaz, presence_detectee, date_mesure "
            "FROM mesures_capteurs ORDER BY id DESC LIMIT %s", (limit,), fetch=True)
        return [{"temperature": float(t), "humidity": float(h), "gas": float(g), "pir": int(bool(p)), "ts": d}
                for t, h, g, p, d in reversed(rows)]

    def recent_alerts(self, limit: int) -> list[dict]:
        rows = self._run(
            "SELECT id, type_alerte, gravite, message, date_creation, acquittee "
            "FROM alertes ORDER BY id DESC LIMIT %s", (limit,), fetch=True)
        alerts = []
        for i, t, g, m, d, a in rows:
            source, message = "", m or ""
            if message.startswith("[") and "] " in message:  # prefixe ajoute par add_alert
                source, message = message[1:].split("] ", 1)
            alerts.append({"id": i, "type": t, "severity": g, "message": message, "source": source,
                           "timestamp": d.isoformat(), "acknowledged": a, "data": {}})
        return alerts

    def devices(self) -> list[dict]:
        rows = self._run("SELECT nom_boitier, statut, wifi_connecte, adresse_ip, date_mise_a_jour "
                         "FROM statut_boitier ORDER BY nom_boitier", fetch=True)
        return [{"node_id": n, "statut": s, "wifi": w, "ip": str(ip) if ip else None,
                 "updated": d.isoformat(timespec="seconds")} for n, s, w, ip, d in rows]

    def healthy(self) -> bool:
        try:
            self._run("SELECT 1")
            return True
        except Exception:
            return False
