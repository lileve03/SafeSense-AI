"""Small transactional SQLite store. Runtime data only; never writes research artifacts."""
import json
import os
import sqlite3
from pathlib import Path
from threading import RLock
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.getenv('SAFESENSE_DB_PATH', str(ROOT / 'runtime/safesense.sqlite3')))
LOCK = RLock()

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=15)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id))')
    db.execute('PRAGMA user_version=1')
    try:
        with db: yield db
    finally:
        db.close()

def put(kind, identifier, value):
    with LOCK, connection() as db:
        db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)', (kind, identifier, json.dumps(value)))

def all_rows(kind):
    with LOCK, connection() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT body FROM records WHERE kind=? ORDER BY rowid', (kind,))]

def get(kind, identifier):
    with LOCK, connection() as db:
        row = db.execute('SELECT body FROM records WHERE kind=? AND id=?', (kind, identifier)).fetchone()
        return json.loads(row[0]) if row else None

def snapshot(events, incidents):
    # Preserve dedup IDs across restart, but never reuse process-local monotonic times.
    with LOCK, connection() as db:
        for kind, values in [('event', events), ('incident', incidents)]:
            for row in values:
                body = {k:v for k,v in row.items() if k != '_monotonic'}
                db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?)', (kind, row['id'], json.dumps(body)))

def clear_demo():
    with LOCK, connection() as db:
        db.execute("DELETE FROM records WHERE kind IN ('event','incident')")
