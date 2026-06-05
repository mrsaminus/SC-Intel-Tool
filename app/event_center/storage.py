import json
import sqlite3

from .models import NotificationEvent


MAX_EVENT_COUNT = 1000


def ensure_event_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_event_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        source TEXT,
        entity_name TEXT,
        event_type TEXT,
        message TEXT,
        metadata_json TEXT,
        severity TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_events_read ON notification_events(is_read, created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_notification_events_category ON notification_events(category, severity)"
    )


def add_notification_event(
    category,
    source,
    entity_name,
    event_type,
    message,
    metadata=None,
    severity="Info",
    dedupe=True,
):
    ensure_event_tables()
    metadata_json = json_dumps(metadata or {})
    with get_connection() as conn:
        cur = conn.cursor()
        if dedupe:
            cur.execute("""
            SELECT id
            FROM notification_events
            WHERE category = ?
              AND source = ?
              AND entity_name = ?
              AND event_type = ?
              AND message = ?
              AND is_read = 0
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """, (category, source, entity_name, event_type, message))
            existing = cur.fetchone()
            if existing:
                return existing[0]

        cur.execute("""
        INSERT INTO notification_events (
            category,
            source,
            entity_name,
            event_type,
            message,
            metadata_json,
            severity
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
            source,
            entity_name,
            event_type,
            message,
            metadata_json,
            severity,
        ))
        event_id = cur.lastrowid
        trim_old_events(cur, MAX_EVENT_COUNT)
        conn.commit()
        return event_id


def list_notification_events(
    query="",
    category="All",
    severity="All",
    unread_only=False,
    limit=1000,
):
    ensure_event_tables()
    params = []
    where = []
    if category and category != "All":
        where.append("category = ?")
        params.append(category)
    if severity and severity != "All":
        where.append("severity = ?")
        params.append(severity)
    if unread_only:
        where.append("is_read = 0")
    if query:
        where.append("""
        (
            LOWER(category) LIKE ?
            OR LOWER(source) LIKE ?
            OR LOWER(entity_name) LIKE ?
            OR LOWER(event_type) LIKE ?
            OR LOWER(message) LIKE ?
            OR LOWER(metadata_json) LIKE ?
        )
        """)
        token = f"%{query.lower()}%"
        params.extend([token] * 6)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT *
        FROM notification_events
        {where_sql}
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
        """, params)
        return [event_from_row(row) for row in cur.fetchall()]


def get_notification_event(event_id):
    ensure_event_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM notification_events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        return event_from_row(row) if row else None


def mark_notification_events_read(event_id=None):
    ensure_event_tables()
    where_sql = "WHERE id = ?" if event_id is not None else ""
    params = (event_id,) if event_id is not None else ()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE notification_events SET is_read = 1 {where_sql}", params)
        conn.commit()
        return cur.rowcount


def delete_read_notification_events():
    ensure_event_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM notification_events WHERE is_read = 1")
        conn.commit()
        return cur.rowcount


def notification_event_counts():
    ensure_event_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS count FROM notification_events")
        total = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM notification_events WHERE is_read = 0")
        unread = cur.fetchone()["count"]
        cur.execute("""
        SELECT category, COUNT(*) AS count
        FROM notification_events
        WHERE is_read = 0
        GROUP BY category
        ORDER BY category
        """)
        categories = {row["category"]: row["count"] for row in cur.fetchall()}
    return {"total": total, "unread": unread, "categories": categories}


def trim_old_events(cursor, limit):
    cursor.execute("""
    DELETE FROM notification_events
    WHERE id NOT IN (
        SELECT id
        FROM notification_events
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
    )
    """, (limit,))


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


def event_from_row(row):
    return NotificationEvent(
        id=row["id"],
        category=row["category"] or "",
        source=row["source"] or "",
        entity_name=row["entity_name"] or "",
        event_type=row["event_type"] or "",
        message=row["message"] or "",
        metadata=json_loads(row["metadata_json"]),
        severity=row["severity"] or "Info",
        created_at=row["created_at"] or "",
        is_read=bool(row["is_read"]),
    )
