"""Durable shared reply queue. Unique source IDs prevent duplicate submissions."""
import json
import random
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / 'out' / 'reply_queue.sqlite3'


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS replies (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, due REAL NOT NULL)')
    return conn


def enqueue(drafts):
    added = 0
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        last = conn.execute('SELECT MAX(due) FROM replies').fetchone()[0] or 0
        for draft in drafts:
            if conn.execute('SELECT 1 FROM replies WHERE id=?', (str(draft['id']),)).fetchone():
                continue
            last = max(time.time(), last) + random.uniform(30, 60) * 60
            conn.execute('INSERT INTO replies VALUES (?, ?, ?, ?)',
                         (str(draft['id']), json.dumps(draft), 'pending', last))
            added += 1
    return added


def next_reply():
    with connect() as conn:
        row = conn.execute("SELECT * FROM replies WHERE status='pending' ORDER BY due, rowid LIMIT 1").fetchone()
        return dict(row) if row else None


def finish(tweet_id, status):
    """Delay remaining items after a late wake so replies never catch up in a burst."""
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('UPDATE replies SET status=?, due=? WHERE id=?', (status, time.time(), str(tweet_id)))
        last = time.time()
        for row in conn.execute("SELECT id, due FROM replies WHERE status='pending' ORDER BY due, rowid").fetchall():
            due = max(row['due'], last + random.uniform(30, 60) * 60)
            conn.execute('UPDATE replies SET due=? WHERE id=?', (due, row['id']))
            last = due


def import_legacy():
    pending = ROOT / 'out' / 'pending_replies.json'
    if pending.exists():
        enqueue(json.loads(pending.read_text()))
        pending.unlink()
