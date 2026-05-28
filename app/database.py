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
            org_sid TEXT,
            org_piracy INTEGER DEFAULT 0,
            any_org_piracy INTEGER DEFAULT 0,
            profile_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        ensure_column(cur, "lookup_history", "org_sid", "TEXT")
        ensure_column(cur, "lookup_history", "org_piracy", "INTEGER DEFAULT 0")
        ensure_column(cur, "lookup_history", "any_org_piracy", "INTEGER DEFAULT 0")
        cur.execute("""
        UPDATE lookup_history
        SET any_org_piracy = 1
        WHERE org_piracy = 1
          AND (any_org_piracy IS NULL OR any_org_piracy = 0)
        """)
        dedupe_lookup_history(cur)

        conn.commit()


def ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_lookup(
    handle,
    display_name,
    main_org,
    profile_url,
    org_sid=None,
    org_piracy=False,
    any_org_piracy=None,
    refresh_timestamp=True,
):
    if any_org_piracy is None:
        any_org_piracy = org_piracy

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
        SELECT id
        FROM lookup_history
        WHERE LOWER(handle) = LOWER(?)
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 1
        """, (handle,))
        existing = cur.fetchone()

        if existing:
            timestamp_sql = ", created_at = CURRENT_TIMESTAMP" if refresh_timestamp else ""
            cur.execute(f"""
            UPDATE lookup_history
            SET
                handle = ?,
                display_name = ?,
                main_org = ?,
                org_sid = ?,
                org_piracy = ?,
                any_org_piracy = ?,
                profile_url = ?
                {timestamp_sql}
            WHERE id = ?
            """, (
                handle,
                display_name,
                main_org,
                org_sid,
                1 if org_piracy else 0,
                1 if any_org_piracy else 0,
                profile_url,
                existing[0],
            ))
            cur.execute("""
            DELETE FROM lookup_history
            WHERE LOWER(handle) = LOWER(?) AND id != ?
            """, (handle, existing[0]))
        else:
            cur.execute("""
            INSERT INTO lookup_history (
                handle,
                display_name,
                main_org,
                org_sid,
                org_piracy,
                any_org_piracy,
                profile_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                handle,
                display_name,
                main_org,
                org_sid,
                1 if org_piracy else 0,
                1 if any_org_piracy else 0,
                profile_url,
            ))

        conn.commit()


def get_lookup_history(limit=200):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT
            handle,
            display_name,
            main_org,
            org_sid,
            org_piracy,
            any_org_piracy,
            profile_url,
            created_at
        FROM lookup_history
        ORDER BY datetime(created_at) DESC, id DESC
        """)

        history = []
        seen_handles = set()
        for row in cur.fetchall():
            row_dict = dict(row)
            handle_key = row_dict["handle"].strip().lower()
            if handle_key in seen_handles:
                continue

            seen_handles.add(handle_key)
            history.append(row_dict)
            if len(history) >= limit:
                break

        return history


def delete_lookup_history(handle):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM lookup_history WHERE LOWER(handle) = LOWER(?)",
            (handle,),
        )
        conn.commit()
        return cur.rowcount


def clear_lookup_history():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM lookup_history")
        conn.commit()
        return cur.rowcount


def dedupe_lookup_history(cursor):
    cursor.execute("""
    SELECT id, handle
    FROM lookup_history
    ORDER BY LOWER(handle), datetime(created_at) DESC, id DESC
    """)

    seen_handles = set()
    duplicate_ids = []
    for row_id, handle in cursor.fetchall():
        handle_key = handle.strip().lower()
        if handle_key in seen_handles:
            duplicate_ids.append(row_id)
        else:
            seen_handles.add(handle_key)

    if not duplicate_ids:
        return

    placeholders = ",".join("?" for _ in duplicate_ids)
    cursor.execute(
        f"DELETE FROM lookup_history WHERE id IN ({placeholders})",
        duplicate_ids,
    )


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
