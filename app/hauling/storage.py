import hashlib
import json
import sqlite3

from .manifest import build_manifest
from .models import (
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUSES,
    HaulingContract,
    HaulingSession,
)


def ensure_hauling_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_hauling_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hauling_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        selected_ship TEXT,
        ship_capacity_scu REAL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        archived_at TEXT,
        total_scu REAL DEFAULT 0,
        loaded_scu REAL DEFAULT 0,
        delivered_scu REAL DEFAULT 0,
        completion_percentage REAL DEFAULT 0,
        notes TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hauling_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        contract_id TEXT NOT NULL,
        pickup TEXT,
        delivery TEXT,
        commodity TEXT,
        scu REAL DEFAULT 0,
        reward REAL,
        source_text_hash TEXT,
        confidence REAL DEFAULT 0,
        status TEXT,
        state TEXT,
        created_at TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        warnings_json TEXT,
        FOREIGN KEY(session_id) REFERENCES hauling_sessions(id) ON DELETE CASCADE,
        UNIQUE(session_id, contract_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hauling_sessions_status ON hauling_sessions(status, updated_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hauling_contracts_session ON hauling_contracts(session_id)")


def save_session(name, manifest, session_id=None, status=None, notes=""):
    ensure_hauling_tables()
    manifest = build_manifest(manifest.contracts, selected_ship=manifest.selected_ship)
    status = normalize_session_status(status or infer_session_status(manifest))
    name = clean_session_name(name, manifest)
    completed_at_sql = "CURRENT_TIMESTAMP" if status == SESSION_STATUS_COMPLETED else "NULL"

    with get_connection() as conn:
        cur = conn.cursor()
        if session_id:
            cur.execute("""
            UPDATE hauling_sessions
            SET name = ?,
                selected_ship = ?,
                ship_capacity_scu = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP,
                completed_at = CASE WHEN ? = 'completed' THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END,
                archived_at = CASE WHEN ? != 'archived' THEN NULL ELSE archived_at END,
                total_scu = ?,
                loaded_scu = ?,
                delivered_scu = ?,
                completion_percentage = ?,
                notes = ?
            WHERE id = ?
            """, (
                name,
                manifest.selected_ship,
                manifest.ship_capacity_scu,
                status,
                status,
                status,
                manifest.total_scu,
                manifest.loaded_scu,
                manifest.delivered_scu,
                manifest.completion_percentage,
                notes,
                session_id,
            ))
            if cur.rowcount == 0:
                session_id = None

        if not session_id:
            cur.execute(f"""
            INSERT INTO hauling_sessions (
                name,
                selected_ship,
                ship_capacity_scu,
                status,
                completed_at,
                total_scu,
                loaded_scu,
                delivered_scu,
                completion_percentage,
                notes
            )
            VALUES (?, ?, ?, ?, {completed_at_sql}, ?, ?, ?, ?, ?)
            """, (
                name,
                manifest.selected_ship,
                manifest.ship_capacity_scu,
                status,
                manifest.total_scu,
                manifest.loaded_scu,
                manifest.delivered_scu,
                manifest.completion_percentage,
                notes,
            ))
            session_id = cur.lastrowid

        replace_session_contracts(cur, session_id, manifest.contracts)
        conn.commit()

    return load_session(session_id)


def replace_session_contracts(cursor, session_id, contracts):
    cursor.execute("DELETE FROM hauling_contracts WHERE session_id = ?", (session_id,))
    for contract in contracts or ():
        cursor.execute("""
        INSERT INTO hauling_contracts (
            session_id,
            contract_id,
            pickup,
            delivery,
            commodity,
            scu,
            reward,
            source_text_hash,
            confidence,
            status,
            state,
            created_at,
            notes,
            warnings_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            contract.id,
            contract.pickup,
            contract.delivery,
            contract.commodity,
            contract.scu,
            contract.reward,
            source_text_hash(contract.source_text),
            contract.confidence,
            contract.status,
            contract.state,
            contract.created_at,
            contract.notes,
            json.dumps(tuple(contract.warnings or ()), ensure_ascii=True),
        ))


def load_session(session_id):
    ensure_hauling_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM hauling_sessions WHERE id = ?", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        contracts = list_session_contracts(cur, session_id)
    return session_from_row(row, contracts)


def list_sessions(include_archived=True, limit=100):
    ensure_hauling_tables()
    where_sql = "" if include_archived else "WHERE status != 'archived'"
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT *
        FROM hauling_sessions
        {where_sql}
        ORDER BY datetime(updated_at) DESC, id DESC
        LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return tuple(session_from_row(row, contracts=()) for row in rows)


def archive_session(session_id):
    ensure_hauling_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        UPDATE hauling_sessions
        SET status = 'archived',
            archived_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (session_id,))
        conn.commit()
        return cur.rowcount


def delete_session(session_id):
    ensure_hauling_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM hauling_contracts WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM hauling_sessions WHERE id = ?", (session_id,))
        rowcount = cur.rowcount
        conn.commit()
        return rowcount


def list_session_contracts(cursor, session_id):
    cursor.execute("""
    SELECT *
    FROM hauling_contracts
    WHERE session_id = ?
    ORDER BY id
    """, (session_id,))
    return tuple(contract_from_row(row) for row in cursor.fetchall())


def session_from_row(row, contracts):
    manifest = build_manifest(contracts, selected_ship=row["selected_ship"] or "")
    return HaulingSession(
        id=row["id"],
        name=row["name"] or "",
        status=normalize_session_status(row["status"]),
        selected_ship=row["selected_ship"] or "",
        ship_capacity_scu=row["ship_capacity_scu"],
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
        completed_at=row["completed_at"] or "",
        archived_at=row["archived_at"] or "",
        total_scu=row["total_scu"] or manifest.total_scu,
        loaded_scu=row["loaded_scu"] or manifest.loaded_scu,
        delivered_scu=row["delivered_scu"] or manifest.delivered_scu,
        completion_percentage=row["completion_percentage"] or manifest.completion_percentage,
        notes=row["notes"] or "",
        manifest=manifest,
    )


def contract_from_row(row):
    return HaulingContract(
        id=row["contract_id"] or "",
        pickup=row["pickup"] or "",
        delivery=row["delivery"] or "",
        commodity=row["commodity"] or "",
        scu=row["scu"] or 0.0,
        reward=row["reward"],
        source_text="",
        confidence=row["confidence"] or 0.0,
        status=row["status"] or "needs_review",
        state=row["state"] or "planned",
        created_at=row["created_at"] or "",
        notes=row["notes"] or "",
        warnings=tuple(json_loads(row["warnings_json"], [])),
    )


def infer_session_status(manifest):
    if manifest.contracts and manifest.delivered_contracts == len(manifest.contracts):
        return SESSION_STATUS_COMPLETED
    return SESSION_STATUS_ACTIVE


def normalize_session_status(status):
    status = str(status or "").strip().lower()
    return status if status in SESSION_STATUSES else SESSION_STATUS_ACTIVE


def clean_session_name(name, manifest):
    name = str(name or "").strip()
    if name:
        return name
    if manifest.selected_ship:
        return f"{manifest.selected_ship} Hauling Session"
    return "Hauling Session"


def source_text_hash(text):
    text = str(text or "")
    if not text:
        return ""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def get_connection():
    from app.database import get_connection as database_get_connection

    return database_get_connection()
