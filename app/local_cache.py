import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone


CACHE_TTL_HOURS = 6
ITEM_FINDER_CACHE_KEY = "item_finder.reference"
WIKELO_CACHE_KEY = "wikelo.items"
UEX_PRICES_CACHE_KEY = "uex_prices"
ITEM_FINDER_SCHEMA_VERSION = "1"
WIKELO_SCHEMA_VERSION = "1"
UEX_PRICES_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class CacheMetadata:
    cache_key: str
    source: str
    schema_version: str
    last_updated: str
    expires_at: str
    row_count: int
    status: str
    error_message: str

    @property
    def last_updated_datetime(self):
        return parse_cache_datetime(self.last_updated)

    @property
    def expires_at_datetime(self):
        return parse_cache_datetime(self.expires_at)


def ensure_cache_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_metadata (
        cache_key TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        row_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        error_message TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_item_finder_items (
        cache_key TEXT NOT NULL,
        source TEXT NOT NULL,
        item_id TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        item_type TEXT,
        availability TEXT,
        detail_url TEXT,
        category_url TEXT,
        effect TEXT,
        payload_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (cache_key, source, item_id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_cache_item_finder_items_name
    ON cache_item_finder_items (cache_key, name)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_item_finder_locations (
        cache_key TEXT NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (cache_key, name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_wikelo_items (
        item_id TEXT PRIMARY KEY,
        item_name TEXT NOT NULL,
        category TEXT,
        item_type TEXT,
        reward_method TEXT,
        mission_name TEXT,
        reward_item TEXT,
        location TEXT,
        source_sheet TEXT,
        source_url TEXT,
        notes TEXT,
        updated TEXT,
        retired INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_wikelo_requirements (
        item_id TEXT NOT NULL,
        requirement_index INTEGER NOT NULL,
        name TEXT NOT NULL,
        quantity TEXT,
        source TEXT,
        PRIMARY KEY (item_id, requirement_index)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_uex_prices (
        cache_key TEXT NOT NULL,
        commodity_name TEXT NOT NULL,
        price_buy REAL,
        price_sell REAL,
        terminal_name TEXT,
        star_system_name TEXT,
        location_name TEXT,
        date_modified INTEGER,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (cache_key, sort_order)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_cache_uex_prices_commodity
    ON cache_uex_prices (cache_key, commodity_name)
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_cache_uex_prices_location
    ON cache_uex_prices (cache_key, star_system_name, location_name, terminal_name)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_uex_commodities (
        cache_key TEXT NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (cache_key, name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache_uex_locations (
        cache_key TEXT NOT NULL,
        name TEXT NOT NULL,
        star_system_name TEXT,
        location_name TEXT,
        terminal_name TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (cache_key, name)
    )
    """)


def get_cache_metadata(cache_key):
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("""
            SELECT cache_key, source, schema_version, last_updated, expires_at,
                   row_count, status, COALESCE(error_message, '')
            FROM cache_metadata
            WHERE cache_key = ?
        """, (cache_key,))
        row = cur.fetchone()

    if not row:
        return None

    return CacheMetadata(
        cache_key=row[0],
        source=row[1],
        schema_version=row[2],
        last_updated=row[3],
        expires_at=row[4],
        row_count=int(row[5] or 0),
        status=row[6],
        error_message=row[7] or "",
    )


def cache_exists(cache_key):
    metadata = get_cache_metadata(cache_key)
    return bool(metadata and metadata.status in {"ready", "stale", "error"} and metadata.row_count > 0)


def cache_is_fresh(cache_key, now=None):
    metadata = get_cache_metadata(cache_key)
    if not metadata or metadata.status != "ready" or metadata.row_count <= 0:
        return False

    expires_at = metadata.expires_at_datetime
    if not expires_at:
        return False

    return expires_at > (now or utc_now())


def cache_status(cache_key, now=None):
    metadata = get_cache_metadata(cache_key)
    if not metadata or metadata.row_count <= 0:
        return "missing"
    if metadata.status == "error":
        return "error"
    if cache_is_fresh(cache_key, now=now):
        return "fresh"
    return "stale"


def update_cache_metadata(
    cache_key,
    source,
    schema_version,
    row_count,
    status="ready",
    error_message="",
    updated_at=None,
    ttl_hours=CACHE_TTL_HOURS,
):
    updated_at = updated_at or utc_now()
    expires_at = updated_at + timedelta(hours=ttl_hours)
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("""
            INSERT INTO cache_metadata (
                cache_key, source, schema_version, last_updated, expires_at,
                row_count, status, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                source = excluded.source,
                schema_version = excluded.schema_version,
                last_updated = excluded.last_updated,
                expires_at = excluded.expires_at,
                row_count = excluded.row_count,
                status = excluded.status,
                error_message = excluded.error_message
        """, (
            cache_key,
            source,
            str(schema_version),
            format_cache_datetime(updated_at),
            format_cache_datetime(expires_at),
            int(row_count or 0),
            status,
            error_message or "",
        ))
        conn.commit()


def mark_cache_error(cache_key, source, schema_version, error_message):
    existing = get_cache_metadata(cache_key)
    row_count = existing.row_count if existing else 0
    update_cache_metadata(
        cache_key,
        source,
        schema_version,
        row_count,
        status="error",
        error_message=str(error_message or ""),
        updated_at=utc_now(),
        ttl_hours=0,
    )


def invalidate_cache(cache_key):
    metadata = get_cache_metadata(cache_key)
    if not metadata:
        return

    update_cache_metadata(
        cache_key,
        metadata.source,
        metadata.schema_version,
        metadata.row_count,
        status="stale",
        error_message=metadata.error_message,
        updated_at=utc_now() - timedelta(hours=CACHE_TTL_HOURS + 1),
    )


def save_item_finder_cache(items, cstone_locations, warnings=None):
    warnings = warnings or []
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("DELETE FROM cache_item_finder_items WHERE cache_key = ?", (ITEM_FINDER_CACHE_KEY,))
        cur.execute("DELETE FROM cache_item_finder_locations WHERE cache_key = ?", (ITEM_FINDER_CACHE_KEY,))

        for sort_order, item in enumerate(items):
            payload_type, payload = serialize_item_finder_item(item)
            cur.execute("""
                INSERT INTO cache_item_finder_items (
                    cache_key, source, item_id, name, category, item_type,
                    availability, detail_url, category_url, effect,
                    payload_type, payload_json, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ITEM_FINDER_CACHE_KEY,
                str(getattr(item, "source", "")),
                str(getattr(item, "item_id", "")),
                str(getattr(item, "name", "")),
                str(getattr(item, "category", "")),
                str(getattr(item, "item_type", "")),
                str(getattr(item, "availability", "")),
                str(getattr(item, "detail_url", "")),
                str(getattr(item, "category_url", "")),
                str(getattr(item, "effect", "")),
                payload_type,
                json.dumps(payload, sort_keys=True),
                sort_order,
            ))

        seen_locations = set()
        for sort_order, location in enumerate(cstone_locations or []):
            location = str(location or "").strip()
            key = location.lower()
            if not location or key in seen_locations:
                continue
            seen_locations.add(key)
            cur.execute("""
                INSERT OR REPLACE INTO cache_item_finder_locations (cache_key, name, sort_order)
                VALUES (?, ?, ?)
            """, (ITEM_FINDER_CACHE_KEY, location, sort_order))

        update_cache_metadata_in_cursor(
            cur,
            ITEM_FINDER_CACHE_KEY,
            "Cornerstone + SC Focus",
            ITEM_FINDER_SCHEMA_VERSION,
            len(items),
            status="ready",
            error_message="; ".join(warnings),
        )
        conn.commit()


def load_item_finder_cache():
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("""
            SELECT payload_type, payload_json
            FROM cache_item_finder_items
            WHERE cache_key = ?
            ORDER BY sort_order, source, name
        """, (ITEM_FINDER_CACHE_KEY,))
        items = [
            deserialize_item_finder_item(payload_type, json.loads(payload_json))
            for payload_type, payload_json in cur.fetchall()
        ]
        cur.execute("""
            SELECT name
            FROM cache_item_finder_locations
            WHERE cache_key = ?
            ORDER BY sort_order, name
        """, (ITEM_FINDER_CACHE_KEY,))
        locations = [row[0] for row in cur.fetchall()]

    return items, locations, get_cache_metadata(ITEM_FINDER_CACHE_KEY)


def save_wikelo_cache(items, warnings=None):
    warnings = warnings or []
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("DELETE FROM cache_wikelo_requirements")
        cur.execute("DELETE FROM cache_wikelo_items")

        for sort_order, item in enumerate(items):
            cur.execute("""
                INSERT OR REPLACE INTO cache_wikelo_items (
                    item_id, item_name, category, item_type, reward_method,
                    mission_name, reward_item, location, source_sheet,
                    source_url, notes, updated, retired, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.item_id,
                item.item_name,
                item.category,
                item.item_type,
                item.reward_method,
                item.mission_name,
                item.reward_item,
                item.location,
                item.source_sheet,
                item.source_url,
                item.notes,
                item.updated,
                1 if item.retired else 0,
                sort_order,
            ))
            for requirement_index, requirement in enumerate(item.requirements):
                cur.execute("""
                    INSERT INTO cache_wikelo_requirements (
                        item_id, requirement_index, name, quantity, source
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    item.item_id,
                    requirement_index,
                    requirement.name,
                    requirement.quantity,
                    requirement.source,
                ))

        update_cache_metadata_in_cursor(
            cur,
            WIKELO_CACHE_KEY,
            "Public Wikelo spreadsheet",
            WIKELO_SCHEMA_VERSION,
            len(items),
            status="ready",
            error_message="; ".join(warnings),
        )
        conn.commit()


def load_wikelo_cache():
    from app.wikelo_client import WikeloItem, WikeloRequirement

    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("""
            SELECT item_id, item_name, category, item_type, reward_method,
                   mission_name, reward_item, location, source_sheet,
                   source_url, notes, updated, retired
            FROM cache_wikelo_items
            ORDER BY sort_order, item_name
        """)
        item_rows = cur.fetchall()
        cur.execute("""
            SELECT item_id, name, quantity, source
            FROM cache_wikelo_requirements
            ORDER BY item_id, requirement_index
        """)
        requirement_rows = cur.fetchall()

    requirements_by_item = {}
    for item_id, name, quantity, source in requirement_rows:
        requirements_by_item.setdefault(item_id, []).append(
            WikeloRequirement(name=name, quantity=quantity or "", source=source or "")
        )

    items = [
        WikeloItem(
            item_id=row[0],
            item_name=row[1],
            category=row[2] or "",
            item_type=row[3] or "",
            reward_method=row[4] or "",
            mission_name=row[5] or "",
            requirements=tuple(requirements_by_item.get(row[0], [])),
            reward_item=row[6] or "",
            location=row[7] or "",
            source_sheet=row[8] or "",
            source_url=row[9] or "",
            notes=row[10] or "",
            updated=row[11] or "",
            retired=bool(row[12]),
        )
        for row in item_rows
    ]
    return items, get_cache_metadata(WIKELO_CACHE_KEY)


def save_uex_prices_cache(prices, warnings=None):
    warnings = warnings or []
    prices = list(prices or [])
    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("DELETE FROM cache_uex_prices WHERE cache_key = ?", (UEX_PRICES_CACHE_KEY,))
        cur.execute("DELETE FROM cache_uex_commodities WHERE cache_key = ?", (UEX_PRICES_CACHE_KEY,))
        cur.execute("DELETE FROM cache_uex_locations WHERE cache_key = ?", (UEX_PRICES_CACHE_KEY,))

        for sort_order, price in enumerate(prices):
            cur.execute("""
                INSERT INTO cache_uex_prices (
                    cache_key, commodity_name, price_buy, price_sell,
                    terminal_name, star_system_name, location_name,
                    date_modified, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                UEX_PRICES_CACHE_KEY,
                price.commodity_name,
                price.price_buy,
                price.price_sell,
                price.terminal_name,
                price.star_system_name,
                price.location_name,
                price.date_modified,
                sort_order,
            ))

        for sort_order, commodity in enumerate(unique_uex_commodities(prices)):
            cur.execute("""
                INSERT OR REPLACE INTO cache_uex_commodities (cache_key, name, sort_order)
                VALUES (?, ?, ?)
            """, (UEX_PRICES_CACHE_KEY, commodity, sort_order))

        for sort_order, location in enumerate(unique_uex_locations(prices)):
            cur.execute("""
                INSERT OR REPLACE INTO cache_uex_locations (
                    cache_key, name, star_system_name, location_name, terminal_name, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                UEX_PRICES_CACHE_KEY,
                location["name"],
                location["star_system_name"],
                location["location_name"],
                location["terminal_name"],
                sort_order,
            ))

        update_cache_metadata_in_cursor(
            cur,
            UEX_PRICES_CACHE_KEY,
            "UEX public market prices",
            UEX_PRICES_SCHEMA_VERSION,
            len(prices),
            status="ready",
            error_message="; ".join(warnings),
        )
        conn.commit()


def load_uex_prices_cache():
    from app.uex_client import UEXCommodityPrice

    with _connect() as conn:
        cur = conn.cursor()
        ensure_cache_tables(cur)
        cur.execute("""
            SELECT commodity_name, price_buy, price_sell, terminal_name,
                   star_system_name, location_name, date_modified
            FROM cache_uex_prices
            WHERE cache_key = ?
            ORDER BY sort_order
        """, (UEX_PRICES_CACHE_KEY,))
        rows = cur.fetchall()

    prices = [
        UEXCommodityPrice(
            commodity_name=row[0] or "Unknown",
            price_buy=row[1],
            price_sell=row[2],
            terminal_name=row[3] or "N/A",
            star_system_name=row[4] or "N/A",
            location_name=row[5] or "N/A",
            date_modified=row[6],
        )
        for row in rows
    ]
    return prices, get_cache_metadata(UEX_PRICES_CACHE_KEY)


def serialize_item_finder_item(item):
    payload = asdict(item)
    if item.__class__.__name__ == "SCFocusShipItem":
        return "scfocus_ship", payload

    return "cstone_item", payload


def deserialize_item_finder_item(payload_type, payload):
    if payload_type == "scfocus_ship":
        from app.scfocus_client import SCFocusShipItem, SCFocusShipLocation

        locations = tuple(
            SCFocusShipLocation(
                location=location.get("location", ""),
                price=location.get("price", ""),
                verified=location.get("verified", ""),
                url=location.get("url", ""),
            )
            for location in payload.get("locations", ())
        )
        payload = dict(payload)
        payload["locations"] = locations
        return SCFocusShipItem(**payload)

    from app.cstone_client import CStoneItem

    return CStoneItem(**payload)


def unique_uex_commodities(prices):
    return sorted({
        price.commodity_name
        for price in prices
        if price.commodity_name and price.commodity_name != "Unknown"
    }, key=str.lower)


def unique_uex_locations(prices):
    locations = {}
    for price in prices:
        name = uex_cache_location_name(price)
        if name == "N/A":
            continue
        key = name.lower()
        if key in locations:
            continue
        locations[key] = {
            "name": name,
            "star_system_name": price.star_system_name,
            "location_name": price.location_name,
            "terminal_name": price.terminal_name,
        }

    return [
        locations[key]
        for key in sorted(locations)
    ]


def uex_cache_location_name(price):
    parts = [
        value
        for value in (
            price.star_system_name if price.star_system_name != "N/A" else "",
            price.location_name if price.location_name != "N/A" else "",
            price.terminal_name if price.terminal_name != "N/A" else "",
        )
        if value
    ]
    return " - ".join(parts) or "N/A"


def update_cache_metadata_in_cursor(
    cursor,
    cache_key,
    source,
    schema_version,
    row_count,
    status="ready",
    error_message="",
    updated_at=None,
    ttl_hours=CACHE_TTL_HOURS,
):
    updated_at = updated_at or utc_now()
    expires_at = updated_at + timedelta(hours=ttl_hours)
    cursor.execute("""
        INSERT INTO cache_metadata (
            cache_key, source, schema_version, last_updated, expires_at,
            row_count, status, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            source = excluded.source,
            schema_version = excluded.schema_version,
            last_updated = excluded.last_updated,
            expires_at = excluded.expires_at,
            row_count = excluded.row_count,
            status = excluded.status,
            error_message = excluded.error_message
    """, (
        cache_key,
        source,
        str(schema_version),
        format_cache_datetime(updated_at),
        format_cache_datetime(expires_at),
        int(row_count or 0),
        status,
        error_message or "",
    ))


def utc_now():
    return datetime.now(timezone.utc)


def format_cache_datetime(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_cache_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _connect():
    from app.database import get_connection

    return get_connection()
