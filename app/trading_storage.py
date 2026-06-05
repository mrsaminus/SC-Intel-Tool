from dataclasses import dataclass


ROUTE_FIELDS = (
    "source",
    "commodity",
    "buy_location",
    "sell_location",
    "buy_price",
    "sell_price",
    "profit_per_scu",
    "cargo_scu",
    "buy_cost",
    "total_profit",
    "quality",
    "notes",
)


@dataclass(frozen=True)
class TradingRouteRecord:
    id: int | None = None
    source: str = ""
    commodity: str = ""
    buy_location: str = ""
    sell_location: str = ""
    buy_price: float | None = None
    sell_price: float | None = None
    profit_per_scu: float | None = None
    cargo_scu: float | None = None
    buy_cost: float | None = None
    total_profit: float | None = None
    quality: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class TradingPresetRecord:
    id: int | None = None
    name: str = ""
    selected_ship: str = ""
    cargo_scu: str = ""
    max_investment: str = ""
    min_profit_per_scu: str = ""
    min_total_profit: str = ""
    show_unprofitable: bool = False
    only_full_cargo: bool = False
    only_affordable: bool = False
    hide_suspicious_margins: bool = False
    created_at: str = ""
    updated_at: str = ""


def ensure_trading_tables(cursor=None):
    if cursor is None:
        with get_connection() as conn:
            ensure_trading_tables(conn.cursor())
            conn.commit()
        return

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_saved_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        commodity TEXT,
        buy_location TEXT,
        sell_location TEXT,
        buy_price REAL,
        sell_price REAL,
        profit_per_scu REAL,
        cargo_scu REAL,
        buy_cost REAL,
        total_profit REAL,
        quality TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_recent_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        commodity TEXT,
        buy_location TEXT,
        sell_location TEXT,
        buy_price REAL,
        sell_price REAL,
        profit_per_scu REAL,
        cargo_scu REAL,
        buy_cost REAL,
        total_profit REAL,
        quality TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trading_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        selected_ship TEXT,
        cargo_scu TEXT,
        max_investment TEXT,
        min_profit_per_scu TEXT,
        min_total_profit TEXT,
        show_unprofitable INTEGER DEFAULT 0,
        only_full_cargo INTEGER DEFAULT 0,
        only_affordable INTEGER DEFAULT 0,
        hide_suspicious_margins INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)


def save_trading_route(record):
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        existing_id = find_saved_route_id(cur, record)
        if existing_id is not None:
            cur.execute("""
            UPDATE trading_saved_routes
            SET
                quality = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (record.quality, record.notes, existing_id))
            conn.commit()
            return existing_id

        cur.execute(f"""
        INSERT INTO trading_saved_routes ({", ".join(ROUTE_FIELDS)})
        VALUES ({", ".join("?" for _ in ROUTE_FIELDS)})
        """, route_values(record))
        conn.commit()
        return cur.lastrowid


def add_recent_trading_route(record, limit=100):
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        delete_exact_route(cur, "trading_recent_routes", record)
        cur.execute(f"""
        INSERT INTO trading_recent_routes ({", ".join(ROUTE_FIELDS)})
        VALUES ({", ".join("?" for _ in ROUTE_FIELDS)})
        """, route_values(record))
        trim_recent_routes(cur, limit)
        conn.commit()
        return cur.lastrowid


def get_saved_trading_routes():
    ensure_trading_tables()
    with get_connection() as conn:
        conn.row_factory = row_factory
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM trading_saved_routes
        ORDER BY datetime(updated_at) DESC, id DESC
        """)
        return [route_from_row(row) for row in cur.fetchall()]


def get_recent_trading_routes(limit=100):
    ensure_trading_tables()
    with get_connection() as conn:
        conn.row_factory = row_factory
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM trading_recent_routes
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
        """, (limit,))
        return [route_from_row(row) for row in cur.fetchall()]


def delete_saved_trading_route(route_id):
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trading_saved_routes WHERE id = ?", (route_id,))
        conn.commit()
        return cur.rowcount


def clear_recent_trading_routes():
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trading_recent_routes")
        conn.commit()
        return cur.rowcount


def save_trading_preset(preset):
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO trading_presets (
            name,
            selected_ship,
            cargo_scu,
            max_investment,
            min_profit_per_scu,
            min_total_profit,
            show_unprofitable,
            only_full_cargo,
            only_affordable,
            hide_suspicious_margins
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            selected_ship = excluded.selected_ship,
            cargo_scu = excluded.cargo_scu,
            max_investment = excluded.max_investment,
            min_profit_per_scu = excluded.min_profit_per_scu,
            min_total_profit = excluded.min_total_profit,
            show_unprofitable = excluded.show_unprofitable,
            only_full_cargo = excluded.only_full_cargo,
            only_affordable = excluded.only_affordable,
            hide_suspicious_margins = excluded.hide_suspicious_margins,
            updated_at = CURRENT_TIMESTAMP
        """, (
            preset.name,
            preset.selected_ship,
            preset.cargo_scu,
            preset.max_investment,
            preset.min_profit_per_scu,
            preset.min_total_profit,
            1 if preset.show_unprofitable else 0,
            1 if preset.only_full_cargo else 0,
            1 if preset.only_affordable else 0,
            1 if preset.hide_suspicious_margins else 0,
        ))
        conn.commit()


def get_trading_presets():
    ensure_trading_tables()
    with get_connection() as conn:
        conn.row_factory = row_factory
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM trading_presets
        ORDER BY LOWER(name)
        """)
        return [preset_from_row(row) for row in cur.fetchall()]


def delete_trading_preset(name):
    ensure_trading_tables()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM trading_presets WHERE LOWER(name) = LOWER(?)", (name,))
        conn.commit()
        return cur.rowcount


def route_values(record):
    return tuple(getattr(record, field) for field in ROUTE_FIELDS)


def get_connection():
    from app.database import get_connection as database_get_connection

    return database_get_connection()


def find_saved_route_id(cursor, record):
    cursor.execute(
        f"""
        SELECT id
        FROM trading_saved_routes
        WHERE {exact_route_where_clause()}
        ORDER BY datetime(updated_at) DESC, id DESC
        LIMIT 1
        """,
        route_values(record),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def delete_exact_route(cursor, table, record):
    cursor.execute(
        f"DELETE FROM {table} WHERE {exact_route_where_clause()}",
        route_values(record),
    )


def exact_route_where_clause():
    text_fields = {"source", "commodity", "buy_location", "sell_location", "quality", "notes"}
    parts = []
    for field in ROUTE_FIELDS:
        if field in text_fields:
            parts.append(f"IFNULL({field}, '') = IFNULL(?, '')")
        else:
            parts.append(f"IFNULL({field}, -999999999) = IFNULL(?, -999999999)")
    return " AND ".join(parts)


def trim_recent_routes(cursor, limit):
    cursor.execute("""
    DELETE FROM trading_recent_routes
    WHERE id NOT IN (
        SELECT id
        FROM trading_recent_routes
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ?
    )
    """, (limit,))


def row_factory(cursor, row):
    return {
        column[0]: row[index]
        for index, column in enumerate(cursor.description)
    }


def route_from_row(row):
    return TradingRouteRecord(
        id=row.get("id"),
        source=row.get("source") or "",
        commodity=row.get("commodity") or "",
        buy_location=row.get("buy_location") or "",
        sell_location=row.get("sell_location") or "",
        buy_price=row.get("buy_price"),
        sell_price=row.get("sell_price"),
        profit_per_scu=row.get("profit_per_scu"),
        cargo_scu=row.get("cargo_scu"),
        buy_cost=row.get("buy_cost"),
        total_profit=row.get("total_profit"),
        quality=row.get("quality") or "",
        notes=row.get("notes") or "",
        created_at=row.get("created_at") or "",
        updated_at=row.get("updated_at") or "",
    )


def preset_from_row(row):
    return TradingPresetRecord(
        id=row.get("id"),
        name=row.get("name") or "",
        selected_ship=row.get("selected_ship") or "",
        cargo_scu=row.get("cargo_scu") or "",
        max_investment=row.get("max_investment") or "",
        min_profit_per_scu=row.get("min_profit_per_scu") or "",
        min_total_profit=row.get("min_total_profit") or "",
        show_unprofitable=bool(row.get("show_unprofitable")),
        only_full_cargo=bool(row.get("only_full_cargo")),
        only_affordable=bool(row.get("only_affordable")),
        hide_suspicious_margins=bool(row.get("hide_suspicious_margins")),
        created_at=row.get("created_at") or "",
        updated_at=row.get("updated_at") or "",
    )
