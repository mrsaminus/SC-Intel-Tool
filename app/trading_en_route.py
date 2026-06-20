from dataclasses import dataclass
from math import floor

from app.trading_data import (
    TradingEstimate,
    TradingOpportunity,
    format_trade_location,
    is_suspicious_margin,
    max_date_modified,
)
from app.uex_client import fetch_all_commodity_prices


@dataclass(frozen=True)
class EnRouteOpportunity:
    commodity: str
    buy_location: str
    buy_price: float
    sell_location: str
    sell_price: float
    profit_per_scu: float
    cargo_scu: float
    buy_cost: float
    total_profit: float
    margin_percent: float
    source: str
    date_modified: int | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class EnRouteResult:
    routes: list[EnRouteOpportunity]
    price_row_count: int
    buy_row_count: int
    sell_row_count: int
    origin_has_data: bool
    destination_has_data: bool
    message: str


def fetch_uex_en_route_opportunities(**filters):
    prices = fetch_all_commodity_prices()
    return build_uex_en_route_opportunities(prices, **filters)


def build_uex_en_route_opportunities(
    prices,
    *,
    origin,
    destination,
    cargo_scu,
    max_investment=None,
    commodity_filter="",
    min_total_profit=None,
    min_profit_per_scu=None,
    include_unprofitable=False,
    hide_suspicious=False,
):
    prices = list(prices or [])
    origin = (origin or "").strip()
    destination = (destination or "").strip()
    safe_cargo_scu = max(0.0, safe_float(cargo_scu, 0.0))

    if not origin or not destination:
        return empty_result(prices, "Choose both origin and destination before finding En Route opportunities.")
    if safe_cargo_scu <= 0:
        return empty_result(prices, "No cargo capacity. Choose a ship or enter Cargo SCU.")

    origin_has_data = any(location_matches(price, origin) for price in prices)
    destination_has_data = any(location_matches(price, destination) for price in prices)
    buy_rows = [
        price
        for price in prices
        if location_matches(price, origin)
        and price.commodity_name
        and price.commodity_name != "Unknown"
        and price.price_buy is not None
        and price.price_buy > 0
    ]
    sell_rows = [
        price
        for price in prices
        if location_matches(price, destination)
        and price.commodity_name
        and price.commodity_name != "Unknown"
        and price.price_sell is not None
        and price.price_sell > 0
    ]

    if not origin_has_data:
        return route_result(prices, [], buy_rows, sell_rows, origin_has_data, destination_has_data,
                            "No UEX buy/sell data found for this selected origin.")
    if not destination_has_data:
        return route_result(prices, [], buy_rows, sell_rows, origin_has_data, destination_has_data,
                            "No UEX buy/sell data found for this selected destination.")
    if not buy_rows:
        return route_result(prices, [], buy_rows, sell_rows, origin_has_data, destination_has_data,
                            "No UEX buy data found for this selected origin.")
    if not sell_rows:
        return route_result(prices, [], buy_rows, sell_rows, origin_has_data, destination_has_data,
                            "No UEX sell data found for this selected destination.")

    buy_by_commodity = best_buy_rows_by_commodity(buy_rows)
    sell_by_commodity = best_sell_rows_by_commodity(sell_rows)
    commodity_filter_key = normalize_location(commodity_filter)

    routes = []
    for commodity_key, buy_row in buy_by_commodity.items():
        sell_row = sell_by_commodity.get(commodity_key)
        if not sell_row:
            continue

        commodity = buy_row.commodity_name
        if commodity_filter_key and commodity_filter_key not in normalize_location(commodity):
            continue

        buy_price = buy_row.price_buy or 0
        sell_price = sell_row.price_sell or 0
        profit_per_scu = sell_price - buy_price
        if profit_per_scu <= 0 and not include_unprofitable:
            continue
        if min_profit_per_scu is not None and profit_per_scu < min_profit_per_scu:
            continue

        trading_opportunity = TradingOpportunity(
            commodity=commodity,
            buy_location=format_trade_location(buy_row),
            buy_price=buy_price,
            sell_location=format_trade_location(sell_row),
            sell_price=sell_price,
            profit_per_scu=profit_per_scu,
            source="UEX",
            date_modified=max_date_modified(buy_row.date_modified, sell_row.date_modified),
        )
        estimate = calculate_en_route_estimate(trading_opportunity, safe_cargo_scu, max_investment)
        if estimate.effective_cargo_scu <= 0:
            continue
        if min_total_profit is not None and estimate.estimated_total_profit < min_total_profit:
            continue

        suspicious = is_suspicious_margin(trading_opportunity)
        if hide_suspicious and suspicious:
            continue

        routes.append(EnRouteOpportunity(
            commodity=commodity,
            buy_location=trading_opportunity.buy_location,
            buy_price=buy_price,
            sell_location=trading_opportunity.sell_location,
            sell_price=sell_price,
            profit_per_scu=profit_per_scu,
            cargo_scu=estimate.effective_cargo_scu,
            buy_cost=estimate.estimated_buy_cost,
            total_profit=estimate.estimated_total_profit,
            margin_percent=margin_percent(profit_per_scu, buy_price),
            source="UEX",
            date_modified=trading_opportunity.date_modified,
            notes=build_notes(trading_opportunity, estimate, suspicious),
        ))

    routes.sort(key=lambda route: (-route.total_profit, -route.profit_per_scu, route.commodity.lower()))
    message = f"Found {len(routes)} En Route opportunities from UEX prices."
    if not routes:
        message = "No En Route opportunities matched the selected locations and filters."

    return route_result(prices, routes, buy_rows, sell_rows, origin_has_data, destination_has_data, message)


def empty_result(prices, message):
    prices = list(prices or [])
    return route_result(prices, [], [], [], False, False, message)


def route_result(prices, routes, buy_rows, sell_rows, origin_has_data, destination_has_data, message):
    return EnRouteResult(
        routes=list(routes),
        price_row_count=len(prices or []),
        buy_row_count=len(buy_rows),
        sell_row_count=len(sell_rows),
        origin_has_data=origin_has_data,
        destination_has_data=destination_has_data,
        message=message,
    )


def best_buy_rows_by_commodity(rows):
    best = {}
    for row in rows:
        key = normalize_location(row.commodity_name)
        current = best.get(key)
        if current is None or buy_sort_key(row) < buy_sort_key(current):
            best[key] = row
    return best


def best_sell_rows_by_commodity(rows):
    best = {}
    for row in rows:
        key = normalize_location(row.commodity_name)
        current = best.get(key)
        if current is None or sell_sort_key(row) > sell_sort_key(current):
            best[key] = row
    return best


def buy_sort_key(row):
    return (row.price_buy or float("inf"), row.date_modified or 0)


def sell_sort_key(row):
    return (row.price_sell or 0, row.date_modified or 0)


def build_notes(opportunity, estimate, suspicious):
    notes = []
    if estimate.investment_limited:
        notes.append("Budget limited")
    if opportunity.profit_per_scu > 0 and margin_percent(opportunity.profit_per_scu, opportunity.buy_price) < 5:
        notes.append("Low margin")
    if estimate.estimated_total_profit >= 1_000_000 or opportunity.profit_per_scu >= 1_000:
        notes.append("High profit")
    if suspicious:
        notes.append("High margin / possible outlier")
    if opportunity.date_modified is None:
        notes.append("UEX data age unknown")
    return tuple(notes)


def calculate_en_route_estimate(opportunity, cargo_scu, max_investment=None):
    safe_cargo_scu = max(0.0, safe_float(cargo_scu, 0.0))
    full_cargo_buy_cost = opportunity.buy_price * safe_cargo_scu
    effective_cargo_scu = safe_cargo_scu
    safe_investment = max(0.0, safe_float(max_investment, 0.0)) if max_investment is not None else None
    if safe_investment is not None and safe_investment > 0:
        if opportunity.buy_price > 0:
            effective_cargo_scu = min(safe_cargo_scu, floor(safe_investment / opportunity.buy_price))
        else:
            effective_cargo_scu = 0

    effective_cargo_scu = max(0.0, effective_cargo_scu)
    estimated_buy_cost = opportunity.buy_price * effective_cargo_scu
    estimated_total_profit = opportunity.profit_per_scu * effective_cargo_scu
    investment_limited = safe_investment is not None and safe_investment > 0 and effective_cargo_scu < safe_cargo_scu
    full_cargo_affordable = safe_investment is None or safe_investment <= 0 or full_cargo_buy_cost <= safe_investment

    return TradingEstimate(
        cargo_scu=safe_cargo_scu,
        effective_cargo_scu=effective_cargo_scu,
        estimated_buy_cost=estimated_buy_cost,
        estimated_total_profit=estimated_total_profit,
        investment_limited=investment_limited,
        full_cargo_affordable=full_cargo_affordable,
    )


def margin_percent(profit_per_scu, buy_price):
    if not buy_price or buy_price <= 0:
        return 0
    return (profit_per_scu / buy_price) * 100


def location_display_values(prices):
    values = {
        format_trade_location(price)
        for price in prices or []
        if format_trade_location(price) != "N/A"
        and (
            (price.price_buy is not None and price.price_buy > 0)
            or (price.price_sell is not None and price.price_sell > 0)
        )
    }
    return sorted(values, key=str.lower)


def commodity_display_values(prices):
    values = {
        price.commodity_name
        for price in prices or []
        if price.commodity_name and price.commodity_name != "Unknown"
    }
    return sorted(values, key=str.lower)


def location_matches(price, selected_location):
    selected = normalize_location(selected_location)
    if not selected:
        return False

    aliases = location_aliases(price)
    if selected in aliases:
        return True

    full = normalize_location(format_trade_location(price))
    if full and (full.startswith(f"{selected} ") or f" {selected} " in f" {full} "):
        return True

    selected_compact = compact_location(selected)
    compact_aliases = {compact_location(alias) for alias in aliases}
    full_compact = compact_location(full)
    return bool(
        selected_compact
        and (
            selected_compact in compact_aliases
            or full_compact.startswith(selected_compact)
        )
    )


def location_aliases(price):
    parts = [
        value
        for value in (
            clean_location_part(price.star_system_name),
            clean_location_part(price.location_name),
            clean_location_part(price.terminal_name),
        )
        if value
    ]
    candidates = {
        format_trade_location(price),
        " ".join(parts),
        " - ".join(parts),
        " > ".join(parts),
    }
    candidates.update(parts)
    if len(parts) >= 2:
        candidates.add(" ".join(parts[:2]))
        candidates.add(" - ".join(parts[:2]))
        candidates.add(" ".join(parts[1:]))
        candidates.add(" - ".join(parts[1:]))
    return {normalize_location(candidate) for candidate in candidates if normalize_location(candidate)}


def clean_location_part(value):
    if not value or value == "N/A":
        return ""
    return str(value).strip()


def normalize_location(value):
    text = str(value or "").lower()
    normalized = []
    previous_space = False
    for char in text:
        if char.isalnum():
            normalized.append(char)
            previous_space = False
        elif not previous_space:
            normalized.append(" ")
            previous_space = True
    return " ".join("".join(normalized).split())


def compact_location(value):
    return normalize_location(value).replace(" ", "")


def safe_float(value, default=None):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
