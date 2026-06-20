from dataclasses import dataclass

from app.trading_data import format_trade_age, format_trade_location
from app.uex_client import fetch_all_commodity_prices


@dataclass(frozen=True)
class BestBuyerResult:
    commodity: str
    location: str
    terminal: str
    sell_price: float
    quantity_scu: float
    source: str
    date_modified: int | None


def fetch_uex_best_buyers(commodity_name, quantity_scu=1):
    prices = fetch_all_commodity_prices()
    return build_best_buyers(prices, commodity_name, quantity_scu=quantity_scu), len(prices)


def build_best_buyers(prices, commodity_name, quantity_scu=1):
    commodity_key = normalize(commodity_name)
    if not commodity_key:
        return []

    best_by_location = {}
    for price in prices:
        if normalize(price.commodity_name) != commodity_key:
            continue
        if price.price_sell is None or price.price_sell <= 0:
            continue

        location = format_trade_location(price)
        existing = best_by_location.get(location)
        if existing and existing.sell_price >= price.price_sell:
            continue

        best_by_location[location] = BestBuyerResult(
            commodity=price.commodity_name,
            location=location,
            terminal=price.terminal_name,
            sell_price=price.price_sell,
            quantity_scu=max(0, quantity_scu or 0),
            source="UEX",
            date_modified=price.date_modified,
        )

    results = list(best_by_location.values())
    results.sort(
        key=lambda result: (
            -result.sell_price,
            result.location.lower(),
            result.terminal.lower(),
        )
    )
    return results


def normalize(value):
    return " ".join(str(value or "").lower().split())


def format_best_buyer_age(result):
    return format_trade_age(result.date_modified)
