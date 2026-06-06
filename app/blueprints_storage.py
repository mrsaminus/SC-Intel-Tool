import sqlite3


def normalized_material_key(name):
    return " ".join(str(name or "").strip().lower().split())


def ensure_blueprint_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_blueprint_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owned_blueprints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blueprint_key TEXT UNIQUE NOT NULL,
        blueprint_name TEXT,
        source TEXT,
        owned INTEGER DEFAULT 0,
        acquired_at TEXT,
        notes TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS owned_crafting_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_key TEXT UNIQUE NOT NULL,
        material_name TEXT,
        quantity REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)


def get_owned_blueprint_keys():
    ensure_blueprint_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT blueprint_key
        FROM owned_blueprints
        WHERE owned = 1
        """)
        return {row[0] for row in cur.fetchall()}


def list_owned_blueprints():
    ensure_blueprint_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM owned_blueprints
        WHERE owned = 1
        ORDER BY datetime(acquired_at) DESC, blueprint_name COLLATE NOCASE
        """)
        return [dict(row) for row in cur.fetchall()]


def set_blueprint_owned(blueprint_key, blueprint_name, source, owned, notes=""):
    ensure_blueprint_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        if owned:
            cur.execute("""
            INSERT INTO owned_blueprints (
                blueprint_key,
                blueprint_name,
                source,
                owned,
                acquired_at,
                notes
            )
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(blueprint_key) DO UPDATE SET
                blueprint_name = excluded.blueprint_name,
                source = excluded.source,
                owned = 1,
                acquired_at = COALESCE(owned_blueprints.acquired_at, CURRENT_TIMESTAMP),
                notes = CASE
                    WHEN excluded.notes != '' THEN excluded.notes
                    ELSE owned_blueprints.notes
                END,
                updated_at = CURRENT_TIMESTAMP
            """, (blueprint_key, blueprint_name, source, notes or ""))
        else:
            cur.execute("""
            INSERT INTO owned_blueprints (
                blueprint_key,
                blueprint_name,
                source,
                owned,
                notes
            )
            VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(blueprint_key) DO UPDATE SET
                blueprint_name = excluded.blueprint_name,
                source = excluded.source,
                owned = 0,
                updated_at = CURRENT_TIMESTAMP
            """, (blueprint_key, blueprint_name, source, notes or ""))
        conn.commit()


def update_blueprint_notes(blueprint_key, notes):
    ensure_blueprint_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        UPDATE owned_blueprints
        SET notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE blueprint_key = ?
        """, (notes or "", blueprint_key))
        conn.commit()
        return cur.rowcount


def get_owned_crafting_materials():
    ensure_blueprint_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT material_key, material_name, quantity, updated_at
        FROM owned_crafting_materials
        ORDER BY material_name COLLATE NOCASE
        """)
        return {row["material_key"]: dict(row) for row in cur.fetchall()}


def list_owned_crafting_materials():
    ensure_blueprint_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT material_key, material_name, quantity, updated_at
        FROM owned_crafting_materials
        ORDER BY material_name COLLATE NOCASE
        """)
        return [dict(row) for row in cur.fetchall()]


def set_owned_crafting_material(material_name, quantity):
    material_name = str(material_name or "").strip()
    if not material_name:
        raise ValueError("Material name is required.")
    quantity = float(quantity or 0)
    if quantity < 0:
        raise ValueError("Material quantity cannot be negative.")
    material_key = normalized_material_key(material_name)
    ensure_blueprint_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO owned_crafting_materials (
            material_key,
            material_name,
            quantity
        )
        VALUES (?, ?, ?)
        ON CONFLICT(material_key) DO UPDATE SET
            material_name = excluded.material_name,
            quantity = excluded.quantity,
            updated_at = CURRENT_TIMESTAMP
        """, (material_key, material_name, quantity))
        conn.commit()
    return material_key


def delete_owned_crafting_material(material_key):
    ensure_blueprint_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM owned_crafting_materials WHERE material_key = ?",
            (material_key,),
        )
        conn.commit()
        return cur.rowcount


def get_connection():
    from app.database import get_connection as database_get_connection

    return database_get_connection()
