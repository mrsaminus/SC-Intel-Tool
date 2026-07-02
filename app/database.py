import sqlite3

from .blueprints_storage import ensure_blueprint_tables
from .event_center.storage import ensure_event_tables
from .hauling.storage import ensure_hauling_tables
from .local_cache import ensure_cache_tables
from .notes_storage import ensure_notes_tables
from .paths import get_database_path
from .trading_storage import ensure_trading_tables
from .watchlists.storage import ensure_watchlist_tables

DB_PATH = get_database_path()


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
        ensure_column(cur, "lookup_history", "is_favorite", "INTEGER DEFAULT 0")
        ensure_column(cur, "lookup_history", "is_pinned", "INTEGER DEFAULT 0")
        ensure_app_settings_table(cur)
        ensure_wikelo_checklist_table(cur)
        ensure_blueprint_tables(cur)
        ensure_trading_tables(cur)
        ensure_watchlist_tables(cur)
        ensure_event_tables(cur)
        ensure_hauling_tables(cur)
        ensure_cache_tables(cur)
        ensure_notes_tables(cur)
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


def ensure_wikelo_checklist_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wikelo_checklist_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reward_key TEXT NOT NULL,
        option_key TEXT NOT NULL,
        material_key TEXT NOT NULL,
        checked INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(reward_key, option_key, material_key)
    )
    """)


def ensure_app_settings_table(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


def get_app_setting(key, default=""):
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_app_settings_table(cur)
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return default
        return row[0]


def set_app_setting(key, value):
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_app_settings_table(cur)
        cur.execute("""
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """, (key, value))
        conn.commit()


def get_wikelo_checklist_state(reward_key):
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_wikelo_checklist_table(cur)
        cur.execute("""
        SELECT option_key, material_key, checked
        FROM wikelo_checklist_state
        WHERE reward_key = ?
        """, (reward_key,))
        return {
            (option_key, material_key): bool(checked)
            for option_key, material_key, checked in cur.fetchall()
        }


def set_wikelo_checklist_state(reward_key, option_key, material_key, checked):
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_wikelo_checklist_table(cur)
        cur.execute("""
        INSERT INTO wikelo_checklist_state (
            reward_key,
            option_key,
            material_key,
            checked
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(reward_key, option_key, material_key)
        DO UPDATE SET
            checked = excluded.checked,
            updated_at = CURRENT_TIMESTAMP
        """, (
            reward_key,
            option_key,
            material_key,
            1 if checked else 0,
        ))
        conn.commit()


def reset_wikelo_checklist_reward(reward_key):
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_wikelo_checklist_table(cur)
        cur.execute(
            "DELETE FROM wikelo_checklist_state WHERE reward_key = ?",
            (reward_key,),
        )
        conn.commit()
        return cur.rowcount


def reset_all_wikelo_checklist_state():
    with get_connection() as conn:
        cur = conn.cursor()
        ensure_wikelo_checklist_table(cur)
        cur.execute("DELETE FROM wikelo_checklist_state")
        conn.commit()
        return cur.rowcount


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
            is_favorite,
            is_pinned,
            created_at
        FROM lookup_history
        ORDER BY is_pinned DESC, datetime(created_at) DESC, id DESC
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


def set_lookup_history_flag(handle, flag, enabled):
    if flag not in {"is_favorite", "is_pinned"}:
        raise ValueError("Unsupported lookup history flag.")

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            UPDATE lookup_history
            SET {flag} = ?
            WHERE LOWER(handle) = LOWER(?)
            """,
            (1 if enabled else 0, handle),
        )
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
