import sqlite3
from pathlib import Path

DB_PATH = Path("sc_intel.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT UNIQUE NOT NULL,
            tag TEXT,
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS lookup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT NOT NULL,
            display_name TEXT,
            main_org TEXT,
            profile_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()


def save_lookup(handle, display_name, main_org, profile_url):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO lookup_history (handle, display_name, main_org, profile_url)
        VALUES (?, ?, ?, ?)
        """, (handle, display_name, main_org, profile_url))
        conn.commit()


def save_note(handle, tag, notes):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO player_notes (handle, tag, notes)
        VALUES (?, ?, ?)
        ON CONFLICT(handle) DO UPDATE SET
            tag = excluded.tag,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """, (handle, tag, notes))
        conn.commit()


def get_note(handle):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT tag, notes FROM player_notes WHERE handle = ?", (handle,))
        return cur.fetchone()