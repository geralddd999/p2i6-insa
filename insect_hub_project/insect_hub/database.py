import sqlite3
from pathlib import Path
import json, datetime as _dt

DB_PATH = Path("data") / "insect_data.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    csv_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER REFERENCES uploads(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()

def get_db():
    """FastAPI dependency that yields a *thread‑agnostic* SQLite connection.
    `check_same_thread=False` is safe because we create **one connection per
    request**, so it is never shared concurrently; it merely allows Starlette’s
    background template‑rendering thread to reuse the same object.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Helper insert functions ------------------------------------------------

def insert_upload(conn: sqlite3.Connection, day: str, csv_path: str) -> int:
    cur = conn.execute("INSERT INTO uploads(day, csv_path) VALUES (?, ?)", (day, csv_path))
    return cur.lastrowid

def insert_photo(conn: sqlite3.Connection, upload_id: int, path: str):
    conn.execute("INSERT INTO photos(upload_id, file_path) VALUES(?, ?)", (upload_id, path))

def insert_health(conn: sqlite3.Connection, upload_id: int, payload: dict):
    conn.execute("INSERT INTO health(upload_id, payload) VALUES(?, ?)", (upload_id, json.dumps(payload)))

def insert_error(conn: sqlite3.Connection, upload_id: int, payload: dict):
    conn.execute("INSERT INTO errors(upload_id, payload) VALUES(?, ?)", (upload_id, json.dumps(payload)))