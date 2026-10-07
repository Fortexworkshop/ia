"""Registre de presence (SQLite) et regles metier des gestes.

Pouce en haut  -> ARRIVEE (heure d'arrivee)
Pouce de cote  -> PAUSE_DEBUT, puis au geste suivant PAUSE_FIN (retour de pause)
Pouce en bas   -> DEPART (fin de journee ; une pause en cours est cloturee automatiquement)
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from .gestures import Gesture


class Event(str, Enum):
    ARRIVEE = "ARRIVEE"
    PAUSE_DEBUT = "PAUSE_DEBUT"
    PAUSE_FIN = "PAUSE_FIN"
    DEPART = "DEPART"


class Status(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    EN_PAUSE = "en_pause"
    PARTI = "parti"


@dataclass
class Outcome:
    accepted: bool
    events: list[Event]
    message: str


@dataclass
class DaySummary:
    agent: str
    day: date
    arrival: datetime | None
    departure: datetime | None
    pauses: int
    pause_minutes: float
    presence_minutes: float | None  # temps present hors pauses (si parti)
    status: Status


_STATUS_AFTER = {
    None: Status.ABSENT,
    Event.ARRIVEE: Status.PRESENT,
    Event.PAUSE_FIN: Status.PRESENT,
    Event.PAUSE_DEBUT: Status.EN_PAUSE,
    Event.DEPART: Status.PARTI,
}


class AttendanceRegister:
    def __init__(self, db_path: str | Path = ":memory:"):
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                event TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                day TEXT NOT NULL
            )"""
        )
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(events)")]
        if "student" in columns:  # base creee par une ancienne version (colonne "student")
            self.conn.execute("DROP INDEX IF EXISTS idx_events_day")
            self.conn.execute("ALTER TABLE events RENAME COLUMN student TO agent")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_events_day ON events(day, agent)")
        self.conn.commit()

    # --- lecture -----------------------------------------------------------
    def events_for(self, agent: str, day: date) -> list[tuple[Event, datetime]]:
        rows = self.conn.execute(
            "SELECT event, timestamp FROM events WHERE agent = ? AND day = ? ORDER BY id",
            (agent, day.isoformat()),
        ).fetchall()
        return [(Event(e), datetime.fromisoformat(t)) for e, t in rows]

    def status(self, agent: str, day: date) -> Status:
        events = self.events_for(agent, day)
        return _STATUS_AFTER[events[-1][0] if events else None]

    def agents_for(self, day: date) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT agent FROM events WHERE day = ? ORDER BY agent", (day.isoformat(),)
        ).fetchall()
        return [r[0] for r in rows]

    # --- ecriture ----------------------------------------------------------
    def _record(self, agent: str, event: Event, when: datetime) -> None:
        self.conn.execute(
            "INSERT INTO events (agent, event, timestamp, day) VALUES (?, ?, ?, ?)",
            (agent, event.value, when.isoformat(timespec="seconds"), when.date().isoformat()),
        )

    def handle(self, agent: str, gesture: Gesture, when: datetime | None = None) -> Outcome:
        when = when or datetime.now()
        status = self.status(agent, when.date())
        hour = when.strftime("%H:%M")

        if gesture is Gesture.THUMB_UP:
            if status is Status.ABSENT:
                events, msg = [Event.ARRIVEE], f"{agent} : arrivee enregistree a {hour}"
            else:
                return Outcome(False, [], f"{agent} : arrivee deja enregistree aujourd'hui")

        elif gesture is Gesture.THUMB_SIDE:
            if status is Status.PRESENT:
                events, msg = [Event.PAUSE_DEBUT], f"{agent} : depart en pause a {hour}"
            elif status is Status.EN_PAUSE:
                events, msg = [Event.PAUSE_FIN], f"{agent} : retour de pause a {hour}"
            else:
                return Outcome(False, [], f"{agent} : pause impossible (statut {status.value})")

        elif gesture is Gesture.THUMB_DOWN:
            if status is Status.PRESENT:
                events, msg = [Event.DEPART], f"{agent} : fin enregistree a {hour}"
            elif status is Status.EN_PAUSE:
                events, msg = [Event.PAUSE_FIN, Event.DEPART], f"{agent} : pause cloturee, fin a {hour}"
            else:
                return Outcome(False, [], f"{agent} : fin impossible (statut {status.value})")

        else:
            return Outcome(False, [], "aucun geste")

        for event in events:
            self._record(agent, event, when)
        self.conn.commit()
        return Outcome(True, events, msg)

    # --- rapports ----------------------------------------------------------
    def summary(self, agent: str, day: date) -> DaySummary:
        events = self.events_for(agent, day)
        arrival = next((t for e, t in events if e is Event.ARRIVEE), None)
        departure = next((t for e, t in events if e is Event.DEPART), None)
        pauses, pause_seconds, pause_start = 0, 0.0, None
        for event, when in events:
            if event is Event.PAUSE_DEBUT:
                pauses += 1
                pause_start = when
            elif event is Event.PAUSE_FIN and pause_start is not None:
                pause_seconds += (when - pause_start).total_seconds()
                pause_start = None

        presence = None
        if arrival and departure:
            presence = ((departure - arrival).total_seconds() - pause_seconds) / 60
        return DaySummary(
            agent=agent,
            day=day,
            arrival=arrival,
            departure=departure,
            pauses=pauses,
            pause_minutes=round(pause_seconds / 60, 1),
            presence_minutes=round(presence, 1) if presence is not None else None,
            status=_STATUS_AFTER[events[-1][0] if events else None],
        )

    def export_csv(self, day: date, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["agent", "date", "arrivee", "depart", "nb_pauses",
                             "minutes_pause", "minutes_presence", "statut"])
            for agent in self.agents_for(day):
                s = self.summary(agent, day)
                writer.writerow([
                    s.agent, s.day.isoformat(),
                    s.arrival.strftime("%H:%M:%S") if s.arrival else "",
                    s.departure.strftime("%H:%M:%S") if s.departure else "",
                    s.pauses, s.pause_minutes,
                    "" if s.presence_minutes is None else s.presence_minutes,
                    s.status.value,
                ])
        return path

    def close(self) -> None:
        self.conn.close()
