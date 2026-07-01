import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


DEFAULT_NOTE_CATEGORIES = (
    "General",
    "Player Intel",
    "Organization Intel",
    "Mining",
    "Trading",
    "Blueprints",
    "Wikelo",
    "Hauling",
    "Fleet",
    "Other",
)


@dataclass(frozen=True)
class KnowledgeNote:
    id: int | None = None
    title: str = ""
    category: str = "General"
    tags: str = ""
    body: str = ""
    linked_type: str = ""
    linked_key: str = ""
    is_pinned: bool = False
    created_at: str = ""
    modified_at: str = ""


def ensure_notes_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_notes_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        tags TEXT,
        body TEXT,
        linked_type TEXT,
        linked_key TEXT,
        is_pinned INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        modified_at TEXT NOT NULL
    )
    """)

    ensure_column(cursor, "knowledge_notes", "category", "TEXT NOT NULL DEFAULT 'General'")
    ensure_column(cursor, "knowledge_notes", "tags", "TEXT")
    ensure_column(cursor, "knowledge_notes", "body", "TEXT")
    ensure_column(cursor, "knowledge_notes", "linked_type", "TEXT")
    ensure_column(cursor, "knowledge_notes", "linked_key", "TEXT")
    ensure_column(cursor, "knowledge_notes", "is_pinned", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(cursor, "knowledge_notes", "created_at", "TEXT")
    ensure_column(cursor, "knowledge_notes", "modified_at", "TEXT")

    now = utc_timestamp()
    cursor.execute("UPDATE knowledge_notes SET category = 'General' WHERE category IS NULL OR category = ''")
    cursor.execute("UPDATE knowledge_notes SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (now,))
    cursor.execute("UPDATE knowledge_notes SET modified_at = created_at WHERE modified_at IS NULL OR modified_at = ''")

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_notes_category ON knowledge_notes(category, is_pinned)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_knowledge_notes_modified ON knowledge_notes(is_pinned, modified_at)"
    )


def list_notes(query="", category="All", include_body=True, limit=500):
    ensure_notes_tables()
    params = []
    where = []
    if category and category != "All":
        where.append("category = ?")
        params.append(category)
    if query:
        token = f"%{query.strip().lower()}%"
        search_fields = [
            "LOWER(title) LIKE ?",
            "LOWER(category) LIKE ?",
            "LOWER(tags) LIKE ?",
            "LOWER(linked_type) LIKE ?",
            "LOWER(linked_key) LIKE ?",
        ]
        params.extend([token] * len(search_fields))
        if include_body:
            search_fields.append("LOWER(body) LIKE ?")
            params.append(token)
        where.append(f"({' OR '.join(search_fields)})")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(int(limit or 500))
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT *
        FROM knowledge_notes
        {where_sql}
        ORDER BY is_pinned DESC, datetime(modified_at) DESC, id DESC
        LIMIT ?
        """, params)
        return [note_from_row(row) for row in cur.fetchall()]


def get_note(note_id):
    ensure_notes_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM knowledge_notes WHERE id = ?", (note_id,))
        row = cur.fetchone()
    return note_from_row(row) if row else None


def save_note(note):
    ensure_notes_tables()
    title = normalize_title(note.title)
    category = normalize_category(note.category)
    timestamp = utc_timestamp()
    with get_connection() as conn:
        cur = conn.cursor()
        if note.id:
            existing = get_note(note.id)
            if not existing:
                raise ValueError("Note does not exist.")
            cur.execute("""
            UPDATE knowledge_notes
            SET title = ?,
                category = ?,
                tags = ?,
                body = ?,
                linked_type = ?,
                linked_key = ?,
                is_pinned = ?,
                modified_at = ?
            WHERE id = ?
            """, (
                title,
                category,
                normalize_tags(note.tags),
                note.body or "",
                note.linked_type or "",
                note.linked_key or "",
                1 if note.is_pinned else 0,
                timestamp,
                note.id,
            ))
            conn.commit()
            return get_note(note.id)

        cur.execute("""
        INSERT INTO knowledge_notes (
            title, category, tags, body, linked_type, linked_key,
            is_pinned, created_at, modified_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            category,
            normalize_tags(note.tags),
            note.body or "",
            note.linked_type or "",
            note.linked_key or "",
            1 if note.is_pinned else 0,
            timestamp,
            timestamp,
        ))
        note_id = cur.lastrowid
        conn.commit()
    return get_note(note_id)


def delete_note(note_id):
    ensure_notes_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_notes WHERE id = ?", (note_id,))
        conn.commit()
        return cur.rowcount


def duplicate_note(note_id):
    source = get_note(note_id)
    if not source:
        raise ValueError("Note does not exist.")
    return save_note(KnowledgeNote(
        title=f"{source.title} Copy",
        category=source.category,
        tags=source.tags,
        body=source.body,
        linked_type=source.linked_type,
        linked_key=source.linked_key,
        is_pinned=source.is_pinned,
    ))


def note_categories():
    ensure_notes_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT DISTINCT category
        FROM knowledge_notes
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
        """)
        stored = [row[0] for row in cur.fetchall()]
    seen = set()
    categories = []
    for category in (*DEFAULT_NOTE_CATEGORIES, *stored):
        key = category.strip().lower()
        if key and key not in seen:
            seen.add(key)
            categories.append(category.strip())
    return categories


def normalize_title(title):
    title = (title or "").strip()
    return title or "Untitled Note"


def normalize_category(category):
    category = (category or "").strip()
    return category or "General"


def normalize_tags(tags):
    parts = []
    seen = set()
    for raw_tag in str(tags or "").replace(";", ",").split(","):
        tag = raw_tag.strip()
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            parts.append(tag)
    return ", ".join(parts)


def note_from_row(row):
    return KnowledgeNote(
        id=row["id"],
        title=row["title"] or "Untitled Note",
        category=row["category"] or "General",
        tags=row["tags"] or "",
        body=row["body"] or "",
        linked_type=row["linked_type"] or "",
        linked_key=row["linked_key"] or "",
        is_pinned=bool(row["is_pinned"]),
        created_at=row["created_at"] or "",
        modified_at=row["modified_at"] or "",
    )


def ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def get_connection():
    from app.database import get_connection as database_get_connection

    return database_get_connection()
