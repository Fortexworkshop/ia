import sqlite3

from sentinel.roles import RoleBook, ascii_text


def make_db(path, rows):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS people (name TEXT UNIQUE, role TEXT NOT NULL DEFAULT '')")
    conn.execute("DELETE FROM people")
    conn.executemany("INSERT INTO people (name, role) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def test_label_shows_role_without_accents(tmp_path):
    db = tmp_path / "people.db"
    make_db(db, [("Momo", "Agent de sécurité"), ("Alice", "")])
    book = RoleBook(db)
    assert book.label("Momo", now=0) == "Momo - Agent de securite"
    assert book.label("Alice", now=0) == "Alice"      # pas de role : nom seul
    assert book.label("Inconnu", now=0) == "Inconnu"


def test_roles_are_refreshed(tmp_path):
    db = tmp_path / "people.db"
    make_db(db, [("Momo", "Technicien")])
    book = RoleBook(db, refresh_seconds=10)
    assert book.label("Momo", now=0) == "Momo - Technicien"
    make_db(db, [("Momo", "Superviseur")])
    assert book.label("Momo", now=5) == "Momo - Technicien"   # cache
    assert book.label("Momo", now=11) == "Momo - Superviseur"  # relu


def test_missing_database(tmp_path):
    assert RoleBook(tmp_path / "absent.db").label("Momo", now=0) == "Momo"
    assert ascii_text("Énergie") == "Energie"
