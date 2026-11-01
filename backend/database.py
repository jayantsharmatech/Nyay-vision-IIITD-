"""SQLite persistence plus an offline queue table for later synchronization."""
import json
import sqlite3
from pathlib import Path
from settings import settings

DB_PATH = Path(__file__).parent / settings.database_path

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with _connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS scans (scan_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS offline_queue (queue_id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, synced INTEGER DEFAULT 0)")

def save_scan(record):
    with _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO scans(scan_id, created_at, payload) VALUES (?, ?, ?)", (record["scan_id"], record["created_at"], json.dumps(record)))

def get_scan(scan_id):
    with _connect() as conn:
        row = conn.execute("SELECT payload FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
    return json.loads(row["payload"]) if row else None

def list_scans(limit=100):
    with _connect() as conn:
        rows = conn.execute("SELECT payload FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(row["payload"]) for row in rows]

def queue_offline(payload):
    with _connect() as conn:
        conn.execute("INSERT INTO offline_queue(payload) VALUES (?)", (json.dumps(payload),))

def pending_queue():
    with _connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM offline_queue WHERE synced = 0 ORDER BY queue_id").fetchall()]
