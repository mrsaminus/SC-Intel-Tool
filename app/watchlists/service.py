import re

from app.player_intel import (
    affiliation_snapshot,
    main_org_snapshot_from_lookup,
    normalize_piracy_status,
    org_change_events,
    player_change_events,
    player_snapshot_from_lookup,
)
from app.rsi_lookup import RSILookupError, fetch_org_details, lookup_player
from app.trading_data import fetch_trading_opportunities

from .storage import (
    add_watchlist_event,
    add_watchlist_snapshot,
    get_latest_snapshot,
    get_watchlist_entry,
    list_watchlist_entries,
    upsert_watchlist_entry,
)


TRADING_ROUTE = "trading_route"
TRADING_COMMODITY = "trading_commodity"
ITEM = "item"
SHIP = "ship"
PLAYER = "player"
ORG = "org"
BLUEPRINT = "blueprint"
MATERIAL = "material"

TRADING_CATEGORIES = {TRADING_ROUTE, TRADING_COMMODITY}
ITEM_CATEGORIES = {ITEM, SHIP}
INTEL_CATEGORIES = {PLAYER, ORG}
BLUEPRINT_CATEGORIES = {BLUEPRINT, MATERIAL}


def add_trading_route_watch(record):
    metadata = route_record_to_dict(record)
    key = route_key(record)
    name = route_name(record)
    entry_id, created = upsert_watchlist_entry(
        TRADING_ROUTE,
        name,
        key,
        record.source or "UEX",
        metadata,
    )
    value = route_value_from_record(record)
    add_watchlist_snapshot(entry_id, route_status(value), value, "Initial route snapshot from Trading.")
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} route watch: {name}",
    )
    return get_watchlist_entry(entry_id)


def add_trading_commodity_watch(commodity, source="UEX", metadata=None):
    commodity = (commodity or "").strip()
    key = normalized_key(source, commodity)
    entry_id, created = upsert_watchlist_entry(
        TRADING_COMMODITY,
        commodity,
        key,
        source or "UEX",
        metadata or {"commodity": commodity},
    )
    add_watchlist_snapshot(entry_id, "tracked", metadata or {"commodity": commodity}, "Initial commodity watch.")
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} commodity watch: {commodity}",
    )
    return get_watchlist_entry(entry_id)


def add_item_watch(item_name, category, source="", metadata=None, watch_category=None):
    item_name = (item_name or "").strip()
    category = (category or "").strip()
    watch_category = watch_category or (SHIP if category.lower().startswith("ships") or category == "Wikelo" else ITEM)
    key = normalized_key(source, category, item_name)
    entry_id, created = upsert_watchlist_entry(
        watch_category,
        item_name,
        key,
        source,
        metadata or {},
    )
    add_watchlist_snapshot(
        entry_id,
        "tracked",
        metadata or {"category": category, "source": source},
        "Initial Item Finder watch. Live refresh is planned for a later pass.",
    )
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} {display_category(watch_category).lower()} watch: {item_name}",
    )
    return get_watchlist_entry(entry_id)


def add_blueprint_watch(blueprint_name, source="BP Overview", metadata=None):
    blueprint_name = (blueprint_name or "").strip()
    key = normalized_key(source, blueprint_name)
    entry_id, created = upsert_watchlist_entry(
        BLUEPRINT,
        blueprint_name,
        key,
        source,
        metadata or {"blueprint": blueprint_name},
    )
    add_watchlist_snapshot(entry_id, "tracked", metadata or {"blueprint": blueprint_name}, "Initial blueprint watch.")
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} blueprint watch: {blueprint_name}",
    )
    return get_watchlist_entry(entry_id)


def add_material_watch(material_name, source="BP Overview", metadata=None):
    material_name = (material_name or "").strip()
    key = normalized_key(source, material_name)
    entry_id, created = upsert_watchlist_entry(
        MATERIAL,
        material_name,
        key,
        source,
        metadata or {"material": material_name},
    )
    add_watchlist_snapshot(entry_id, "tracked", metadata or {"material": material_name}, "Initial material watch.")
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} material watch: {material_name}",
    )
    return get_watchlist_entry(entry_id)


def add_player_watch(data, tag="", notes=""):
    snapshot = player_snapshot_from_lookup(data, tag=tag, notes=notes)
    return add_player_snapshot_watch(snapshot)


def add_player_snapshot_watch(snapshot):
    handle = snapshot["handle"]
    key = normalized_key("rsi", handle)
    entry_id, created = upsert_watchlist_entry(
        PLAYER,
        handle,
        key,
        "RSI",
        snapshot,
    )
    add_watchlist_snapshot(
        entry_id,
        player_status(snapshot),
        snapshot,
        "Initial player watch snapshot from Player Lookup.",
    )
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} player watch: {handle}",
    )
    return get_watchlist_entry(entry_id)


def add_org_watch(org, source="RSI"):
    snapshot = dict(org or {})
    name = snapshot.get("name") or snapshot.get("sid") or "Unknown Organization"
    sid = snapshot.get("sid") or ""
    key = normalized_key(source, sid or name)
    entry_id, created = upsert_watchlist_entry(
        ORG,
        name,
        key,
        source,
        snapshot,
    )
    add_watchlist_snapshot(
        entry_id,
        org_status(snapshot),
        snapshot,
        "Initial organization watch snapshot.",
    )
    add_watchlist_event(
        entry_id,
        "created" if created else "updated",
        f"{'Added' if created else 'Updated'} organization watch: {name}",
    )
    return get_watchlist_entry(entry_id)


def add_main_org_watch_from_lookup(data):
    org = main_org_snapshot_from_lookup(data)
    if org.get("redacted") or not org.get("sid") or org.get("sid") == "N/A":
        raise ValueError("Main organization is hidden or unavailable and cannot be watched yet.")
    return add_org_watch(org, "RSI")


def add_affiliation_org_watch(org):
    snapshot = affiliation_snapshot(org)
    if snapshot.get("redacted") or not snapshot.get("sid") or snapshot.get("sid") == "N/A":
        raise ValueError("Organization is hidden or unavailable and cannot be watched yet.")
    return add_org_watch(snapshot, "RSI")


def refresh_watchlist_entries(entries):
    entries = list(entries or [])
    if not entries:
        return []

    opportunities = None
    if any(entry.category in TRADING_CATEGORIES for entry in entries):
        opportunities, _price_count = fetch_trading_opportunities(include_unprofitable=True)

    if any(entry.category in INTEL_CATEGORIES for entry in entries):
        clear_rsi_caches()

    results = []
    for entry in entries:
        if entry.category in TRADING_CATEGORIES:
            results.append(refresh_trading_entry(entry, opportunities))
        elif entry.category in ITEM_CATEGORIES:
            results.append(refresh_local_only_entry(entry))
        elif entry.category in BLUEPRINT_CATEGORIES:
            results.append(refresh_blueprint_entry(entry))
        elif entry.category == PLAYER:
            results.append(refresh_player_entry(entry))
        elif entry.category == ORG:
            results.append(refresh_org_entry(entry))
        else:
            results.append(refresh_planned_entry(entry))

    return results


def refresh_trading_entry(entry, opportunities):
    if entry.category == TRADING_ROUTE:
        return refresh_trading_route(entry, opportunities)
    return refresh_trading_commodity(entry, opportunities)


def refresh_trading_route(entry, opportunities):
    metadata = entry.metadata or {}
    commodity = metadata.get("commodity") or entry.name
    buy_location = metadata.get("buy_location") or ""
    sell_location = metadata.get("sell_location") or ""
    cargo_scu = safe_float(metadata.get("cargo_scu"), default=1)

    match = None
    for opportunity in opportunities:
        if normalized_key(opportunity.commodity) != normalized_key(commodity):
            continue
        if normalized_key(opportunity.buy_location) != normalized_key(buy_location):
            continue
        if normalized_key(opportunity.sell_location) != normalized_key(sell_location):
            continue
        match = opportunity
        break

    if not match:
        value = {
            "commodity": commodity,
            "buy_location": buy_location,
            "sell_location": sell_location,
        }
        return record_refresh_result(entry, "no_data", value, "No matching UEX route found.")

    total_profit = match.profit_per_scu * cargo_scu
    buy_cost = match.buy_price * cargo_scu
    value = {
        "commodity": match.commodity,
        "buy_location": match.buy_location,
        "sell_location": match.sell_location,
        "buy_price": match.buy_price,
        "sell_price": match.sell_price,
        "profit_per_scu": match.profit_per_scu,
        "cargo_scu": cargo_scu,
        "buy_cost": buy_cost,
        "total_profit": total_profit,
        "source": match.source,
        "date_modified": match.date_modified,
    }
    status = route_status(value)
    return record_refresh_result(entry, status, value, "UEX route refreshed.")


def refresh_trading_commodity(entry, opportunities):
    commodity = (entry.metadata or {}).get("commodity") or entry.name
    matches = [
        opportunity
        for opportunity in opportunities
        if normalized_key(opportunity.commodity) == normalized_key(commodity)
    ]
    if not matches:
        return record_refresh_result(
            entry,
            "no_data",
            {"commodity": commodity},
            "No UEX commodity rows found.",
        )

    best = max(matches, key=lambda opportunity: opportunity.profit_per_scu)
    value = {
        "commodity": best.commodity,
        "buy_location": best.buy_location,
        "sell_location": best.sell_location,
        "buy_price": best.buy_price,
        "sell_price": best.sell_price,
        "profit_per_scu": best.profit_per_scu,
        "source": best.source,
        "date_modified": best.date_modified,
        "route_count": len(matches),
    }
    return record_refresh_result(entry, route_status(value), value, f"Best of {len(matches)} UEX route(s).")


def refresh_local_only_entry(entry):
    value = dict(entry.metadata or {})
    return record_refresh_result(
        entry,
        "refresh_pending",
        value,
        "Live Item Finder refresh is planned; current metadata remains tracked locally.",
    )


def refresh_blueprint_entry(entry):
    value = dict(entry.metadata or {})
    return record_refresh_result(
        entry,
        "tracked",
        value,
        "Blueprint reference data is tracked locally through BP Overview cache.",
    )


def refresh_player_entry(entry):
    handle = (entry.metadata or {}).get("handle") or entry.name
    previous = get_latest_snapshot(entry.id)
    try:
        data = lookup_player(handle)
    except RSILookupError as exc:
        value = dict(entry.metadata or {})
        value["last_error"] = str(exc)
        return record_refresh_result(
            entry,
            "lookup_failed",
            value,
            f"RSI player lookup failed: {exc}",
            previous=previous,
        )

    value = player_snapshot_from_lookup(
        data,
        tag=(entry.metadata or {}).get("tag", ""),
        notes=(entry.metadata or {}).get("notes", ""),
    )
    status = player_status(value)
    return record_refresh_result(
        entry,
        status,
        value,
        "RSI player watch refreshed.",
        previous=previous,
        forced_events=player_change_events(previous.value if previous else None, value),
    )


def refresh_org_entry(entry):
    previous = get_latest_snapshot(entry.id)
    metadata = entry.metadata or {}
    sid = metadata.get("sid") or ""
    if not sid or sid == "N/A" or metadata.get("redacted"):
        value = dict(metadata)
        return record_refresh_result(
            entry,
            "no_data",
            value,
            "Organization SID is hidden or unavailable.",
            previous=previous,
        )

    details = fetch_org_details(sid)
    value = dict(metadata)
    for key in ("type", "commitment", "exclusivity", "member_count", "url", "logo_url"):
        if details.get(key):
            value[key] = details[key]
    value["piracy"] = "YES" if details.get("piracy") else "NO"
    value["redacted"] = False

    return record_refresh_result(
        entry,
        org_status(value),
        value,
        "RSI organization watch refreshed.",
        previous=previous,
        forced_events=org_change_events(previous.value if previous else None, value),
    )


def refresh_planned_entry(entry):
    return record_refresh_result(
        entry,
        "planned",
        entry.metadata or {},
        "This watch category is planned for a later milestone.",
    )


def record_refresh_result(entry, status, value, notes, previous=None, forced_events=None):
    if previous is None:
        previous = get_latest_snapshot(entry.id)
    add_watchlist_snapshot(entry.id, status, value, notes)
    for event in forced_events or ():
        add_watchlist_event(entry.id, event[0], event[2])

    event = build_refresh_event(entry, previous, status, value)
    if event:
        add_watchlist_event(entry.id, event[0], event[1])
    return get_watchlist_entry(entry.id)


def build_refresh_event(entry, previous, status, value):
    previous_status = previous.status if previous else ""
    previous_value = previous.value if previous else {}

    if status == "no_data" and previous_status != "no_data":
        return "no_data", f"No current data for {entry.name}."
    if status == "lookup_failed" and previous_status != "lookup_failed":
        return "lookup_failed", f"RSI lookup failed for {entry.name}."
    if previous_status == "lookup_failed" and status != "lookup_failed":
        return "lookup_recovered", f"{entry.name} returned after a lookup failure."
    if previous_status == "no_data" and status != "no_data":
        return "recovered", f"{entry.name} has current data again."
    if status == "unprofitable" and previous_status != "unprofitable":
        return "unprofitable", f"{entry.name} is currently unprofitable."
    if status == "profitable" and previous_status == "unprofitable":
        return "profitable", f"{entry.name} is profitable again."
    if status in {"refresh_pending", "planned", "redacted"} and previous_status != status:
        return status, f"{entry.name}: {status_text(status)}."

    changed_keys = changed_value_keys(previous_value, value)
    if changed_keys:
        label = ", ".join(changed_keys[:3])
        return "value_changed", f"{entry.name} changed: {label}."

    return None


def changed_value_keys(previous_value, value):
    keys = ("buy_price", "sell_price", "profit_per_scu", "total_profit", "location_count")
    changed = []
    for key in keys:
        if key not in value:
            continue
        if significant_change(previous_value.get(key), value.get(key)):
            changed.append(key)
    return changed


def significant_change(previous, current, threshold=0.01):
    if previous is None and current is None:
        return False
    prev_num = safe_float(previous)
    curr_num = safe_float(current)
    if prev_num is None or curr_num is None:
        return previous != current
    if prev_num == curr_num:
        return False
    if prev_num == 0:
        return abs(curr_num) > 0
    return abs(curr_num - prev_num) / abs(prev_num) >= threshold


def copy_watchlist_summary_text(entry, latest_snapshot=None):
    latest_snapshot = latest_snapshot or get_latest_snapshot(entry.id)
    value = latest_snapshot.value if latest_snapshot else entry.metadata

    if entry.category == TRADING_ROUTE:
        return "\n".join((
            f"Commodity: {value.get('commodity') or entry.name}",
            f"Buy: {value.get('buy_location') or 'N/A'} @ {format_auec(value.get('buy_price'))} / SCU",
            f"Sell: {value.get('sell_location') or 'N/A'} @ {format_auec(value.get('sell_price'))} / SCU",
            f"Cargo: {format_number(value.get('cargo_scu'))} SCU",
            f"Buy Cost: {format_auec(value.get('buy_cost'))}",
            f"Profit: {format_auec(value.get('total_profit'))}",
            f"Status: {status_text(latest_snapshot.status if latest_snapshot else entry.last_status)}",
            f"Source: {entry.source or value.get('source') or 'N/A'}",
        ))

    if entry.category == TRADING_COMMODITY:
        return "\n".join((
            f"Commodity: {value.get('commodity') or entry.name}",
            f"Best Buy: {value.get('buy_location') or 'N/A'} @ {format_auec(value.get('buy_price'))} / SCU",
            f"Best Sell: {value.get('sell_location') or 'N/A'} @ {format_auec(value.get('sell_price'))} / SCU",
            f"Profit / SCU: {format_auec(value.get('profit_per_scu'))}",
            f"Status: {status_text(latest_snapshot.status if latest_snapshot else entry.last_status)}",
            f"Source: {entry.source or 'N/A'}",
        ))

    if entry.category == PLAYER:
        return "\n".join((
            f"Player: {value.get('handle') or entry.name}",
            f"Display: {value.get('display_name') or 'N/A'}",
            f"Main Org: {value.get('main_org') or 'N/A'}",
            f"Org SID: {value.get('org_sid') or 'N/A'}",
            f"Piracy: {value.get('piracy_status') or 'Unknown'}",
            f"Status: {status_text(latest_snapshot.status if latest_snapshot else entry.last_status)}",
            "Source: RSI",
        ))

    if entry.category == ORG:
        return "\n".join((
            f"Organization: {value.get('name') or entry.name}",
            f"SID: {value.get('sid') or 'N/A'}",
            f"Members: {value.get('member_count') or 'N/A'}",
            f"Type: {value.get('type') or 'N/A'}",
            f"Piracy: {value.get('piracy') or 'Unknown'}",
            f"Status: {status_text(latest_snapshot.status if latest_snapshot else entry.last_status)}",
            "Source: RSI",
        ))

    return "\n".join((
        f"Name: {entry.name}",
        f"Category: {display_category(entry.category)}",
        f"Source: {entry.source or 'N/A'}",
        f"Availability: {value.get('availability') or 'N/A'}",
        f"Locations: {value.get('location_summary') or value.get('location_count') or 'N/A'}",
        f"Status: {status_text(latest_snapshot.status if latest_snapshot else entry.last_status)}",
    ))


def route_record_to_dict(record):
    return {
        "source": record.source,
        "commodity": record.commodity,
        "buy_location": record.buy_location,
        "sell_location": record.sell_location,
        "buy_price": record.buy_price,
        "sell_price": record.sell_price,
        "profit_per_scu": record.profit_per_scu,
        "cargo_scu": record.cargo_scu,
        "buy_cost": record.buy_cost,
        "total_profit": record.total_profit,
        "quality": record.quality,
        "notes": record.notes,
    }


def route_value_from_record(record):
    return route_record_to_dict(record)


def route_key(record):
    return normalized_key(record.source or "UEX", record.commodity, record.buy_location, record.sell_location)


def route_name(record):
    return f"{record.commodity}: {record.buy_location} -> {record.sell_location}"


def route_status(value):
    profit = safe_float(value.get("profit_per_scu"), default=0)
    return "profitable" if profit > 0 else "unprofitable"


def player_status(value):
    if value.get("main_org_redacted") or value.get("affiliations_redacted") or value.get("organizations_redacted"):
        return "redacted"
    if normalize_piracy_status(value.get("piracy_status")) == "YES":
        return "piracy_found"
    return "tracked"


def org_status(value):
    if value.get("redacted"):
        return "redacted"
    if normalize_piracy_status(value.get("piracy")) == "YES":
        return "piracy_found"
    return "tracked"


def display_category(category):
    return {
        TRADING_ROUTE: "Trading Route",
        TRADING_COMMODITY: "Trading Commodity",
        ITEM: "Item",
        SHIP: "Ship",
        PLAYER: "Player",
        ORG: "Organization",
        BLUEPRINT: "Blueprint",
        MATERIAL: "Material",
    }.get(category, category.replace("_", " ").title())


def status_text(status):
    return {
        "tracked": "Tracked",
        "profitable": "Profitable",
        "unprofitable": "Unprofitable",
        "no_data": "No data",
        "recovered": "Recovered",
        "refresh_pending": "Refresh not implemented yet",
        "planned": "Planned",
        "lookup_failed": "Lookup failed",
        "lookup_recovered": "Lookup recovered",
        "redacted": "Redacted / Hidden",
        "piracy_found": "Piracy signal found",
    }.get(status or "", status or "Not checked")


def watchlist_overview_summary():
    from .storage import list_watchlist_entries, list_watchlist_events, overview_counts

    entries = list_watchlist_entries(include_inactive=True)
    active_entries = [entry for entry in entries if entry.is_active]
    counts = overview_counts()
    group_counts = {
        "Intel": sum(1 for entry in active_entries if entry.category in INTEL_CATEGORIES),
        "Items": sum(1 for entry in active_entries if entry.category in ITEM_CATEGORIES),
        "Trading": sum(1 for entry in active_entries if entry.category in TRADING_CATEGORIES),
        "Blueprints": sum(1 for entry in active_entries if entry.category in BLUEPRINT_CATEGORIES),
    }
    source_counts = {}
    status_counts = {}
    for entry in active_entries:
        source_counts[entry.source or "Local"] = source_counts.get(entry.source or "Local", 0) + 1
        status = status_text(entry.last_status)
        status_counts[status] = status_counts.get(status, 0) + 1

    recent_events = list_watchlist_events(limit=10)
    local_data = local_data_watchlist_summary()
    return {
        "total": len(entries),
        "active": counts["active_count"],
        "inactive": len(entries) - counts["active_count"],
        "unread": counts["unread_count"],
        "last_checked": counts["last_checked"],
        "groups": group_counts,
        "categories": counts["categories"],
        "sources": source_counts,
        "statuses": status_counts,
        "recent_activity": len(recent_events),
        "local_data": local_data,
    }


def local_data_watchlist_summary():
    try:
        from app.cache_manager import enumerate_cache_sources
    except Exception:
        return {"available": [], "warnings": ["Local Data Platform unavailable."]}

    sources = list(enumerate_cache_sources())
    available = [source.name for source in sources if source.row_count > 0]
    warnings = [
        f"{source.name}: {source.status}"
        for source in sources
        if source.status in {"Stale", "Offline", "Missing"}
    ]
    return {"available": available, "warnings": warnings}


def clear_rsi_caches():
    if hasattr(lookup_player, "cache_clear"):
        lookup_player.cache_clear()
    if hasattr(fetch_org_details, "cache_clear"):
        fetch_org_details.cache_clear()


def normalized_key(*parts):
    text = " ".join(str(part or "") for part in parts)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_auec(value):
    number = format_number(value)
    return "N/A" if number == "N/A" else f"{number} aUEC"


def format_number(value):
    number = safe_float(value)
    if number is None:
        return "N/A"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")
