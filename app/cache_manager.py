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
    last_success: str
    last_failure: str
    last_error: str
    last_operation_status: str
    last_refresh_duration: str


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
    CacheSourceDefinition(
        key=local_cache.BLUEPRINT_CACHE_KEY,
        name="BP Overview",
        description="Blueprint recipe, material and mission reference rows.",
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
    operation_summary = local_cache.cache_operation_summary(cache_key)
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
        last_success=operation_summary["last_success"],
        last_failure=operation_summary["last_failure"],
        last_error=operation_summary["last_error"] or (metadata.error_message if metadata else ""),
        last_operation_status=operation_summary["last_operation_status"],
        last_refresh_duration=format_duration_ms(operation_summary["last_refresh_duration_ms"]),
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
    rows_before = cache_source_info(cache_key).row_count
    operation_id = local_cache.start_cache_operation(
        cache_key,
        source.name,
        "refresh",
        rows_before=rows_before,
    )
    try:
        if cache_key == local_cache.ITEM_FINDER_CACHE_KEY:
            success, message = refresh_item_finder_cache()
        elif cache_key == local_cache.WIKELO_CACHE_KEY:
            success, message = refresh_wikelo_cache()
        elif cache_key == local_cache.UEX_PRICES_CACHE_KEY:
            success, message = refresh_uex_cache()
        elif cache_key == local_cache.BLUEPRINT_CACHE_KEY:
            success, message = refresh_blueprint_cache()
        else:
            raise ValueError(f"Unknown cache source: {cache_key}")
    except Exception as exc:  # noqa: BLE001 - record cache refresh failures for tester diagnostics.
        info = cache_source_info(cache_key)
        local_cache.finish_cache_operation(
            operation_id,
            "failed",
            rows_after=info.row_count,
            error_message=str(exc),
            details={"cache_status": info.status, "cached_rows_available": info.row_count > 0},
        )
        return CacheRefreshResult(
            key=source.key,
            name=source.name,
            success=False,
            message=str(exc),
            info=info,
        )

    info = cache_source_info(cache_key)
    local_cache.finish_cache_operation(
        operation_id,
        "success" if success else "failed",
        rows_after=info.row_count,
        error_message="" if success else message,
        details={
            "cache_status": info.status,
            "message": message,
            "cached_rows_available": info.row_count > 0,
        },
    )

    return CacheRefreshResult(
        key=source.key,
        name=source.name,
        success=success,
        message=message,
        info=cache_source_info(cache_key),
    )


def refresh_all_cache_sources():
    rows_before = sum(source.row_count for source in enumerate_cache_sources())
    operation_id = local_cache.start_cache_operation(
        "__all__",
        "All cache sources",
        "refresh_all",
        rows_before=rows_before,
    )
    results = []
    try:
        for source in CACHE_SOURCES:
            results.append(refresh_cache_source(source.key))
    finally:
        rows_after = sum(source.row_count for source in enumerate_cache_sources())
        failed = [result for result in results if not result.success]
        status = "success" if not failed and len(results) == len(CACHE_SOURCES) else "partial_failure"
        local_cache.finish_cache_operation(
            operation_id,
            status,
            rows_after=rows_after,
            error_message=f"{len(failed)} source(s) failed" if failed else "",
            details={
                "success_count": len(results) - len(failed),
                "failure_count": len(failed),
                "source_count": len(CACHE_SOURCES),
            },
        )
    return tuple(results)


def clear_cache_source(cache_key):
    source = source_definition(cache_key)
    rows_before = cache_source_info(cache_key).row_count
    operation_id = local_cache.start_cache_operation(
        cache_key,
        source.name,
        "clear",
        rows_before=rows_before,
    )
    try:
        local_cache.clear_cache_key(cache_key)
    except Exception as exc:  # noqa: BLE001 - preserve clear failure details locally.
        info = cache_source_info(source.key)
        local_cache.finish_cache_operation(
            operation_id,
            "failed",
            rows_after=info.row_count,
            error_message=str(exc),
        )
        raise
    info = cache_source_info(source.key)
    local_cache.finish_cache_operation(operation_id, "success", rows_after=info.row_count)
    return info


def clear_all_cached_data():
    rows_before = sum(source.row_count for source in enumerate_cache_sources())
    operation_id = local_cache.start_cache_operation(
        "__all__",
        "All cache sources",
        "clear_all",
        rows_before=rows_before,
    )
    try:
        for source in CACHE_SOURCES:
            clear_cache_source(source.key)
    except Exception as exc:  # noqa: BLE001 - preserve clear-all failure details locally.
        rows_after = sum(source.row_count for source in enumerate_cache_sources())
        local_cache.finish_cache_operation(
            operation_id,
            "failed",
            rows_after=rows_after,
            error_message=str(exc),
        )
        raise
    rows_after = sum(source.row_count for source in enumerate_cache_sources())
    local_cache.finish_cache_operation(operation_id, "success", rows_after=rows_after)
    return enumerate_cache_sources()


def recent_cache_operations(limit=8):
    return local_cache.recent_cache_operations(limit=limit)


def recent_cache_operation_summaries(limit=8):
    return tuple(format_cache_operation(operation) for operation in recent_cache_operations(limit=limit))


def source_definition(cache_key):
    for source in CACHE_SOURCES:
        if source.key == cache_key:
            return source
    raise ValueError(f"Unknown cache source: {cache_key}")


def format_duration_ms(duration_ms):
    if duration_ms is None:
        return "-"
    if duration_ms < 1000:
        return f"{duration_ms} ms"
    return f"{duration_ms / 1000:.1f}s"


def format_cache_operation(operation):
    operation_name = operation.operation.replace("_", " ").title()
    status_name = operation.status.replace("_", " ").title()
    rows = f"{operation.rows_after} rows"
    duration = format_duration_ms(operation.duration_ms)
    message = f"{operation.source} - {operation_name} {status_name} - {rows}"
    if duration != "-":
        message += f" - {duration}"
    if operation.error_message:
        message += f" - {operation.error_message}"
    return message


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


def refresh_blueprint_cache():
    from .blueprints_client import load_blueprints

    snapshot = load_blueprints(force_refresh=True, raise_on_missing=False)
    if snapshot.source_error:
        if snapshot.cache_status == "missing":
            return False, f"Blueprint source unavailable and no cached blueprint rows are available. {snapshot.source_error}"
        return False, f"Blueprint source unavailable; using existing cached rows. {snapshot.source_error}"
    return True, f"Cached {len(snapshot.blueprints)} blueprint rows."
