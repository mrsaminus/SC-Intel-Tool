from app.trading_storage import TradingRouteRecord


def format_route_summary(record):
    lines = [
        f"Commodity: {record.commodity or 'N/A'}",
        f"Buy from: {record.buy_location or 'N/A'} @ {format_auec(record.buy_price)} / SCU",
        f"Sell to: {record.sell_location or 'N/A'} @ {format_auec(record.sell_price)} / SCU",
        f"Profit / SCU: {format_auec(record.profit_per_scu)}",
        f"Cargo used: {format_scu(record.cargo_scu)}",
        f"Buy cost: {format_auec(record.buy_cost)}",
        f"Estimated total profit: {format_auec(record.total_profit)}",
        f"Quality: {record.quality or 'N/A'}",
        f"Source: {record.source or 'N/A'}",
    ]
    if record.notes:
        lines.append(f"Notes: {record.notes}")
    return "\n".join(lines)


def is_complete_route_record(record):
    return all((
        bool(record.source),
        bool(record.commodity),
        bool(record.buy_location),
        bool(record.sell_location),
        record.buy_price is not None,
        record.sell_price is not None,
        record.profit_per_scu is not None,
        record.cargo_scu is not None,
        record.buy_cost is not None,
        record.total_profit is not None,
    ))


def format_auec(value):
    if value is None:
        return "N/A"
    return f"{format_number(value)} aUEC"


def format_scu(value):
    if value is None:
        return "N/A"
    return f"{format_number(value)} SCU"


def format_number(value):
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def notes_from_flags(flags, extra_notes=()):
    notes = [
        note
        for note in [*flags, *extra_notes]
        if note
    ]
    return ", ".join(notes) if notes else "None"


def describe_route_legs(raw):
    if not isinstance(raw, dict):
        return ""

    for key in ("legs", "steps", "transactions", "edges"):
        value = raw.get(key)
        if isinstance(value, list) and len(value) > 1:
            descriptions = [
                describe_route_leg(leg)
                for leg in value[:5]
            ]
            descriptions = [description for description in descriptions if description]
            if descriptions:
                suffix = ""
                if len(value) > len(descriptions):
                    suffix = f" (+{len(value) - len(descriptions)} more)"
                return f"Legs: {' | '.join(descriptions)}{suffix}"

    return ""


def describe_route_leg(leg):
    if not isinstance(leg, dict):
        return ""

    parts = []
    for key in ("origin", "from", "start", "source"):
        value = compact_value(leg.get(key))
        if value:
            parts.append(value)
            break

    for key in ("destination", "to", "end", "target"):
        value = compact_value(leg.get(key))
        if value:
            parts.append(value)
            break

    commodity = compact_value(leg.get("commodity") or leg.get("commodityName") or leg.get("itemName"))
    if commodity:
        parts.append(commodity)

    return " -> ".join(parts)


def compact_value(value):
    if isinstance(value, dict):
        return str(
            value.get("locationAndShop")
            or value.get("name")
            or value.get("location")
            or value.get("shop")
            or ""
        ).strip()
    if value is None:
        return ""
    return str(value).strip()
