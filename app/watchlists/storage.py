import json
import sqlite3

from .models import WatchlistEntry, WatchlistEvent, WatchlistSnapshot


def ensure_watchlist_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_watchlist_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        key TEXT NOT NULL,
        source TEXT,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_checked_at TEXT,
        last_status TEXT,
        is_active INTEGER DEFAULT 1,
        UNIQUE(category, key)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watchlist_id INTEGER NOT NULL,
        checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT,
        value_json TEXT,
        notes TEXT,
        FOREIGN KEY(watchlist_id) REFERENCES watchlist_entries(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        watchlist_id INTEGER NOT NULL,
        event_type TEXT,
        message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0,
        FOREIGN KEY(watchlist_id) REFERENCES watchlist_entries(id) ON DELETE CASCADE
    )
    """)

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_watchlist_entries_category ON watchlist_entries(category, is_active)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_watchlist_snapshots_watchlist ON watchlist_snapshots(watchlist_id, checked_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_watchlist_events_watchlist ON watchlist_events(watchlist_id, is_read)"
    )


def upsert_watchlist_entry(category, name, key, source="", metadata=None):
    ensure_watchlist_tables()
    metadata_json = json_dumps(metadata or {})
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM watchlist_entries WHERE category = ? AND key = ?",
            (category, key),
        )
        existing = cur.fetchone()
        if existing:
            entry_id = existing[0]
            cur.execute("""
            UPDATE watchlist_entries
            SET
                name = ?,
                source = ?,
                metadata_json = ?,
                updated_at = CURRENT_TIMESTAMP,
                is_active = 1
            WHERE id = ?
            """, (name, source, metadata_json, entry_id))
            conn.commit()
            return entry_id, False

        cur.execute("""
        INSERT INTO watchlist_entries (category, name, key, source, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        """, (category, name, key, source, metadata_json))
        conn.commit()
        return cur.lastrowid, True


def get_watchlist_entry(entry_id):
    ensure_watchlist_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT e.*,
               COALESCE(unread.unread_events, 0) AS unread_events
        FROM watchlist_entries e
        LEFT JOIN (
            SELECT watchlist_id, COUNT(*) AS unread_events
            FROM watchlist_events
            WHERE is_read = 0
            GROUP BY watchlist_id
        ) unread ON unread.watchlist_id = e.id
        WHERE e.id = ?
        """, (entry_id,))
        row = cur.fetchone()
        return entry_from_row(row) if row else None


def list_watchlist_entries(categories=None, include_inactive=True):
    ensure_watchlist_tables()
    categories = tuple(categories or ())
    params = []
    where = []
    if categories:
        where.append(f"e.category IN ({','.join('?' for _ in categories)})")
        params.extend(categories)
    if not include_inactive:
        where.append("e.is_active = 1")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT e.*,
               COALESCE(unread.unread_events, 0) AS unread_events
        FROM watchlist_entries e
        LEFT JOIN (
            SELECT watchlist_id, COUNT(*) AS unread_events
            FROM watchlist_events
            WHERE is_read = 0
            GROUP BY watchlist_id
        ) unread ON unread.watchlist_id = e.id
        {where_sql}
        ORDER BY e.is_active DESC, datetime(e.updated_at) DESC, e.id DESC
        """, params)
        return [entry_from_row(row) for row in cur.fetchall()]


def add_watchlist_snapshot(watchlist_id, status, value=None, notes=""):
    ensure_watchlist_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO watchlist_snapshots (watchlist_id, status, value_json, notes)
        VALUES (?, ?, ?, ?)
        """, (watchlist_id, status, json_dumps(value or {}), notes))
        cur.execute("""
        UPDATE watchlist_entries
        SET
            last_checked_at = CURRENT_TIMESTAMP,
            last_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, watchlist_id))
        conn.commit()
        return cur.lastrowid


def get_latest_snapshot(watchlist_id):
    ensure_watchlist_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM watchlist_snapshots
        WHERE watchlist_id = ?
        ORDER BY datetime(checked_at) DESC, id DESC
        LIMIT 1
        """, (watchlist_id,))
        row = cur.fetchone()
        return snapshot_from_row(row) if row else None


def list_watchlist_snapshots(watchlist_id, limit=20):
    ensure_watchlist_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM watchlist_snapshots
        WHERE watchlist_id = ?
        ORDER BY datetime(checked_at) DESC, id DESC
        LIMIT ?
        """, (watchlist_id, limit))
        return [snapshot_from_row(row) for row in cur.fetchall()]


def add_watchlist_event(watchlist_id, event_type, message):
    ensure_watchlist_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO watchlist_events (watchlist_id, event_type, message)
        VALUES (?, ?, ?)
        """, (watchlist_id, event_type, message))
        event_id = cur.lastrowid
        cur.execute("""
        SELECT e.*,
               COALESCE(unread.unread_events, 0) AS unread_events
        FROM watchlist_entries e
        LEFT JOIN (
            SELECT watchlist_id, COUNT(*) AS unread_events
            FROM watchlist_events
            WHERE is_read = 0
            GROUP BY watchlist_id
        ) unread ON unread.watchlist_id = e.id
        WHERE e.id = ?
        """, (watchlist_id,))
        entry = entry_from_row(cur.fetchone())
        conn.commit()

    if entry:
        try:
            from app.event_center.service import record_watchlist_event

            record_watchlist_event(entry, event_type, message)
        except Exception:
            pass

    return event_id


def list_watchlist_events(watchlist_id=None, limit=20, unread_only=False):
    ensure_watchlist_tables()
    params = []
    where = []
    if watchlist_id is not None:
        where.append("watchlist_id = ?")
        params.append(watchlist_id)
    if unread_only:
        where.append("is_read = 0")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT *
        FROM watchlist_events
        {where_sql}
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
        """, params)
        return [event_from_row(row) for row in cur.fetchall()]


def mark_watchlist_events_read(watchlist_id=None):
    ensure_watchlist_tables()
    where_sql = "WHERE watchlist_id = ?" if watchlist_id is not None else ""
    params = (watchlist_id,) if watchlist_id is not None else ()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE watchlist_events SET is_read = 1 {where_sql}", params)
        conn.commit()
        return cur.rowcount


def set_watchlist_active(watchlist_id, active):
    ensure_watchlist_tables()
    entry = get_watchlist_entry(watchlist_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        UPDATE watchlist_entries
        SET is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (1 if active else 0, watchlist_id))
        conn.commit()
        changed = cur.rowcount
    if changed and entry:
        add_watchlist_event(
            watchlist_id,
            "enabled" if active else "disabled",
            f"{'Enabled' if active else 'Disabled'} watch: {entry.name}",
        )
    return changed


def delete_watchlist_entry(watchlist_id):
    ensure_watchlist_tables()
    entry = get_watchlist_entry(watchlist_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM watchlist_snapshots WHERE watchlist_id = ?", (watchlist_id,))
        cur.execute("DELETE FROM watchlist_events WHERE watchlist_id = ?", (watchlist_id,))
        cur.execute("DELETE FROM watchlist_entries WHERE id = ?", (watchlist_id,))
        conn.commit()
        changed = cur.rowcount
    if changed and entry:
        record_watchlist_deleted(entry)
    return changed


def record_watchlist_deleted(entry):
    try:
        from app.event_center.service import record_event

        record_event(
            category="Watchlists",
            source=entry.source or "Watchlists",
            entity_name=entry.name,
            event_type="deleted",
            message=f"Removed watchlist entry: {entry.name}",
            metadata={
                "watchlist_id": entry.id,
                "watchlist_category": entry.category,
                "watchlist_key": entry.key,
            },
            severity="Info",
            dedupe=False,
        )
    except Exception:
        pass


def overview_counts():
    ensure_watchlist_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS count FROM watchlist_entries WHERE is_active = 1")
        active_count = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM watchlist_events WHERE is_read = 0")
        unread_count = cur.fetchone()["count"]
        cur.execute("""
        SELECT MAX(last_checked_at) AS last_checked
        FROM watchlist_entries
        WHERE last_checked_at IS NOT NULL
        """)
        last_checked = cur.fetchone()["last_checked"] or "Never"
        cur.execute("""
        SELECT category, COUNT(*) AS count
        FROM watchlist_entries
        WHERE is_active = 1
        GROUP BY category
        ORDER BY category
        """)
        categories = {row["category"]: row["count"] for row in cur.fetchall()}

    return {
        "active_count": active_count,
        "unread_count": unread_count,
        "last_checked": last_checked,
        "categories": categories,
    }


def json_dumps(value):
    return json.dumps(value or {}, sort_keys=True, ensure_ascii=True)


def json_loads(value):
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def get_connection():
    from app.database import get_connection as database_get_connection

    return database_get_connection()


def entry_from_row(row):
    if row is None:
        return None
    return WatchlistEntry(
        id=row["id"],
        category=row["category"] or "",
        name=row["name"] or "",
        key=row["key"] or "",
        source=row["source"] or "",
        metadata=json_loads(row["metadata_json"]),
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
        last_checked_at=row["last_checked_at"] or "",
        last_status=row["last_status"] or "",
        is_active=bool(row["is_active"]),
        unread_events=int(row["unread_events"] or 0) if "unread_events" in row.keys() else 0,
    )


def snapshot_from_row(row):
    return WatchlistSnapshot(
        id=row["id"],
        watchlist_id=row["watchlist_id"],
        checked_at=row["checked_at"] or "",
        status=row["status"] or "",
        value=json_loads(row["value_json"]),
        notes=row["notes"] or "",
    )


def event_from_row(row):
    return WatchlistEvent(
        id=row["id"],
        watchlist_id=row["watchlist_id"],
        event_type=row["event_type"] or "",
        message=row["message"] or "",
        created_at=row["created_at"] or "",
        is_read=bool(row["is_read"]),
    )
