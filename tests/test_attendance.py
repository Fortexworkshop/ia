import csv
from datetime import date, datetime

from presence.attendance import AttendanceRegister, Event, Status
from presence.gestures import Gesture

DAY = date(2026, 10, 5)


def at(hour, minute):
    return datetime(2026, 10, 5, hour, minute)


def test_full_day_with_toilet_break(tmp_path):
    reg = AttendanceRegister()
    assert reg.handle("alice", Gesture.THUMB_UP, at(8, 30)).events == [Event.ARRIVEE]
    assert reg.handle("alice", Gesture.THUMB_SIDE, at(10, 0)).events == [Event.PAUSE_DEBUT]
    assert reg.status("alice", DAY) is Status.EN_PAUSE
    assert reg.handle("alice", Gesture.THUMB_SIDE, at(10, 6)).events == [Event.PAUSE_FIN]
    assert reg.handle("alice", Gesture.THUMB_DOWN, at(17, 0)).events == [Event.DEPART]

    s = reg.summary("alice", DAY)
    assert s.arrival == at(8, 30) and s.departure == at(17, 0)
    assert s.pauses == 1 and s.pause_minutes == 6
    assert s.presence_minutes == 8.5 * 60 - 6
    assert s.status is Status.PARTI

    rows = list(csv.reader(reg.export_csv(DAY, tmp_path / "p.csv").open(encoding="utf-8"), delimiter=";"))
    assert rows[1] == ["alice", "2026-10-05", "08:30:00", "17:00:00", "1", "6.0", "504.0", "parti"]


def test_refused_transitions():
    reg = AttendanceRegister()
    assert not reg.handle("bob", Gesture.THUMB_SIDE, at(8, 0)).accepted   # pause avant arrivee
    assert not reg.handle("bob", Gesture.THUMB_DOWN, at(8, 0)).accepted   # fin avant arrivee
    reg.handle("bob", Gesture.THUMB_UP, at(8, 5))
    assert not reg.handle("bob", Gesture.THUMB_UP, at(9, 0)).accepted     # double arrivee
    reg.handle("bob", Gesture.THUMB_DOWN, at(12, 0))
    assert not reg.handle("bob", Gesture.THUMB_SIDE, at(12, 5)).accepted  # pause apres depart


def test_departure_during_break_closes_it():
    reg = AttendanceRegister()
    reg.handle("carla", Gesture.THUMB_UP, at(9, 0))
    reg.handle("carla", Gesture.THUMB_SIDE, at(11, 0))
    out = reg.handle("carla", Gesture.THUMB_DOWN, at(11, 10))
    assert out.events == [Event.PAUSE_FIN, Event.DEPART]
    assert reg.summary("carla", DAY).pause_minutes == 10


def test_new_day_resets_status():
    reg = AttendanceRegister()
    reg.handle("dan", Gesture.THUMB_UP, at(8, 0))
    reg.handle("dan", Gesture.THUMB_DOWN, at(16, 0))
    assert reg.handle("dan", Gesture.THUMB_UP, datetime(2026, 10, 6, 8, 0)).accepted


def test_agents_are_independent():
    reg = AttendanceRegister()
    reg.handle("alice", Gesture.THUMB_UP, at(8, 0))
    assert reg.status("bob", DAY) is Status.ABSENT
    assert reg.agents_for(DAY) == ["alice"]


def test_migrates_old_student_column(tmp_path):
    import sqlite3

    from presence.attendance import AttendanceRegister

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, student TEXT NOT NULL, "
                 "event TEXT NOT NULL, timestamp TEXT NOT NULL, day TEXT NOT NULL)")
    conn.execute("CREATE INDEX idx_events_day ON events(day, student)")
    conn.execute("INSERT INTO events (student, event, timestamp, day) "
                 "VALUES ('Alice', 'ARRIVEE', '2026-10-07T08:00:00', '2026-10-07')")
    conn.commit()
    conn.close()

    from datetime import date
    register = AttendanceRegister(db)
    assert register.agents_for(date(2026, 10, 7)) == ["Alice"]
    register.close()
