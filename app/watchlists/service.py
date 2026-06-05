import re

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

TRADING_CATEGORIES = {TRADING_ROUTE, TRADING_COMMODITY}
ITEM_CATEGORIES = {ITEM, SHIP}


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


def refresh_watchlist_entries(entries):
    entries = list(entries or [])
    if not entries:
        return []

    opportunities = None
    if any(entry.category in TRADING_CATEGORIES for entry in entries):
        opportunities, _price_count = fetch_trading_opportunities(include_unprofitable=True)

    results = []
    for entry in entries:
        if entry.category in TRADING_CATEGORIES:
            results.append(refresh_trading_entry(entry, opportunities))
        elif entry.category in ITEM_CATEGORIES:
            results.append(refresh_local_only_entry(entry))
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


def refresh_planned_entry(entry):
    return record_refresh_result(
        entry,
        "planned",
        entry.metadata or {},
        "This watch category is planned for a later milestone.",
    )


def record_refresh_result(entry, status, value, notes):
    previous = get_latest_snapshot(entry.id)
    add_watchlist_snapshot(entry.id, status, value, notes)
    event = build_refresh_event(entry, previous, status, value)
    if event:
        add_watchlist_event(entry.id, event[0], event[1])
    return get_watchlist_entry(entry.id)


def build_refresh_event(entry, previous, status, value):
    previous_status = previous.status if previous else ""
    previous_value = previous.value if previous else {}

    if status == "no_data" and previous_status != "no_data":
        return "no_data", f"No current data for {entry.name}."
    if previous_status == "no_data" and status != "no_data":
        return "recovered", f"{entry.name} has current data again."
    if status == "unprofitable" and previous_status != "unprofitable":
        return "unprofitable", f"{entry.name} is currently unprofitable."
    if status == "profitable" and previous_status == "unprofitable":
        return "profitable", f"{entry.name} is profitable again."
    if status in {"refresh_pending", "planned"} and previous_status != status:
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


def display_category(category):
    return {
        TRADING_ROUTE: "Trading Route",
        TRADING_COMMODITY: "Trading Commodity",
        ITEM: "Item",
        SHIP: "Ship",
        "player": "Player",
        "org": "Organization",
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
    }.get(status or "", status or "Not checked")


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
