from dataclasses import dataclass
from datetime import timezone

from . import local_cache


@dataclass(frozen=True)
class CacheSourceDefinition:
    key: str
    name: str
    description: str
    refresh_supported: bool = True
    clear_supported: bool = True


@dataclass(frozen=True)
class CacheSourceInfo:
    key: str
    name: str
    description: str
    status: str
    last_updated: str
    age: str
    row_count: int
    schema_version: str
    error_message: str
    refresh_supported: bool
    clear_supported: bool


@dataclass(frozen=True)
class CacheRefreshResult:
    key: str
    name: str
    success: bool
    message: str
    info: CacheSourceInfo


CACHE_SOURCES = (
    CacheSourceDefinition(
        key=local_cache.ITEM_FINDER_CACHE_KEY,
        name="Item Finder",
        description="Cornerstone and SC Focus reference rows.",
    ),
    CacheSourceDefinition(
        key=local_cache.WIKELO_CACHE_KEY,
        name="Wikelo",
        description="Public Wikelo spreadsheet rewards and requirements.",
    ),
    CacheSourceDefinition(
        key=local_cache.UEX_PRICES_CACHE_KEY,
        name="UEX Trading",
        description="UEX market price rows used by Trading workflows.",
    ),
)


def cache_source_definitions():
    return CACHE_SOURCES


def enumerate_cache_sources(now=None):
    return tuple(cache_source_info(source.key, now=now) for source in CACHE_SOURCES)


def cache_source_info(cache_key, now=None):
    source = source_definition(cache_key)
    metadata = local_cache.get_cache_metadata(cache_key)
    status = normalized_cache_status(cache_key, metadata, now=now)
    return CacheSourceInfo(
        key=source.key,
        name=source.name,
        description=source.description,
        status=status,
        last_updated=metadata.last_updated if metadata else "Never",
        age=cache_age(metadata, now=now),
        row_count=metadata.row_count if metadata else 0,
        schema_version=metadata.schema_version if metadata else "-",
        error_message=metadata.error_message if metadata else "",
        refresh_supported=source.refresh_supported,
        clear_supported=source.clear_supported,
    )


def normalized_cache_status(cache_key, metadata=None, now=None):
    metadata = metadata or local_cache.get_cache_metadata(cache_key)
    if not metadata or metadata.row_count <= 0:
        return "Missing"
    if metadata.status == "error":
        return "Offline"
    if local_cache.cache_is_fresh(cache_key, now=now):
        return "Fresh"
    return "Stale"


def cache_age(metadata, now=None):
    if not metadata:
        return "No cache"

    updated_at = metadata.last_updated_datetime
    if not updated_at:
        return "Unknown"

    now = now or local_cache.utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delta = now.astimezone(timezone.utc) - updated_at
    total_seconds = max(0, int(delta.total_seconds()))
    if total_seconds < 60:
        return "Just now"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hr ago"
    days = hours // 24
    return f"{days} days ago"


def refresh_cache_source(cache_key):
    source = source_definition(cache_key)
    if cache_key == local_cache.ITEM_FINDER_CACHE_KEY:
        success, message = refresh_item_finder_cache()
    elif cache_key == local_cache.WIKELO_CACHE_KEY:
        success, message = refresh_wikelo_cache()
    elif cache_key == local_cache.UEX_PRICES_CACHE_KEY:
        success, message = refresh_uex_cache()
    else:
        raise ValueError(f"Unknown cache source: {cache_key}")

    return CacheRefreshResult(
        key=source.key,
        name=source.name,
        success=success,
        message=message,
        info=cache_source_info(cache_key),
    )


def refresh_all_cache_sources():
    results = []
    for source in CACHE_SOURCES:
        results.append(refresh_cache_source(source.key))
    return tuple(results)


def clear_cache_source(cache_key):
    source = source_definition(cache_key)
    local_cache.clear_cache_key(cache_key)
    return cache_source_info(source.key)


def clear_all_cached_data():
    local_cache.clear_all_cache_data()
    return enumerate_cache_sources()


def source_definition(cache_key):
    for source in CACHE_SOURCES:
        if source.key == cache_key:
            return source
    raise ValueError(f"Unknown cache source: {cache_key}")


def refresh_item_finder_cache():
    import requests

    from .cstone_client import CStoneError, fetch_cstone_items, fetch_cstone_location_names
    from .scfocus_client import fetch_scfocus_ship_items

    loaded_items = []
    failed = []
    cstone_locations = []

    try:
        loaded_items.extend(fetch_cstone_items())
    except (CStoneError, requests.RequestException, ValueError) as exc:
        failed.append(f"Cornerstone: {exc}")

    try:
        cstone_locations = fetch_cstone_location_names()
    except (CStoneError, requests.RequestException, ValueError) as exc:
        failed.append(f"Cornerstone locations: {exc}")

    try:
        loaded_items.extend(fetch_scfocus_ship_items())
    except (requests.RequestException, ValueError) as exc:
        failed.append(f"SC Focus: {exc}")

    if loaded_items:
        local_cache.save_item_finder_cache(loaded_items, cstone_locations, failed)
        if failed:
            return True, f"Cached {len(loaded_items)} Item Finder rows with {len(failed)} source warning(s)."
        return True, f"Cached {len(loaded_items)} Item Finder rows."

    message = "; ".join(failed) or "No Item Finder rows were loaded."
    local_cache.mark_cache_error(
        local_cache.ITEM_FINDER_CACHE_KEY,
        "Cornerstone + SC Focus",
        local_cache.ITEM_FINDER_SCHEMA_VERSION,
        message,
    )
    return False, message


def refresh_wikelo_cache():
    from .wikelo_client import fetch_wikelo_items

    try:
        items = list(fetch_wikelo_items())
    except Exception as exc:  # noqa: BLE001 - preserve cache metadata for diagnostics.
        local_cache.mark_cache_error(
            local_cache.WIKELO_CACHE_KEY,
            "Public Wikelo spreadsheet",
            local_cache.WIKELO_SCHEMA_VERSION,
            str(exc),
        )
        return False, str(exc)

    local_cache.save_wikelo_cache(items)
    return True, f"Cached {len(items)} Wikelo rows."


def refresh_uex_cache():
    from .uex_client import load_all_commodity_prices

    snapshot = load_all_commodity_prices(force_refresh=True)
    if snapshot.source_error:
        return False, f"UEX unavailable; using existing cached rows. {snapshot.source_error}"
    return True, f"Cached {len(snapshot.prices)} UEX price rows."
