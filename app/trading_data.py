from dataclasses import dataclass
from datetime import datetime

from app.uex_client import fetch_all_commodity_prices


@dataclass(frozen=True)
class TradingOpportunity:
    commodity: str
    buy_location: str
    buy_price: float
    sell_location: str
    sell_price: float
    profit_per_unit: float
    source: str
    date_modified: int | None


def fetch_trading_opportunities(include_unprofitable=False):
    prices = fetch_all_commodity_prices()
    return build_trading_opportunities(prices, include_unprofitable=include_unprofitable), len(prices)


def build_trading_opportunities(prices, include_unprofitable=False):
    grouped = {}
    for price in prices:
        if not price.commodity_name or price.commodity_name == "Unknown":
            continue

        grouped.setdefault(price.commodity_name, []).append(price)

    opportunities = []
    for commodity, rows in grouped.items():
        buy_rows = [
            row
            for row in rows
            if row.price_buy is not None and row.price_buy > 0
        ]
        sell_rows = [
            row
            for row in rows
            if row.price_sell is not None and row.price_sell > 0
        ]

        for buy_row in buy_rows:
            for sell_row in sell_rows:
                profit = (sell_row.price_sell or 0) - (buy_row.price_buy or 0)
                if profit <= 0 and not include_unprofitable:
                    continue

                opportunities.append(TradingOpportunity(
                    commodity=commodity,
                    buy_location=format_trade_location(buy_row),
                    buy_price=buy_row.price_buy or 0,
                    sell_location=format_trade_location(sell_row),
                    sell_price=sell_row.price_sell or 0,
                    profit_per_unit=profit,
                    source="UEX",
                    date_modified=max_date_modified(buy_row.date_modified, sell_row.date_modified),
                ))

    opportunities.sort(
        key=lambda opportunity: (
            -opportunity.profit_per_unit,
            opportunity.commodity.lower(),
            opportunity.buy_location.lower(),
            opportunity.sell_location.lower(),
        )
    )
    return opportunities


def format_trade_location(price):
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


def max_date_modified(*values):
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None

    return max(valid_values)


def format_trade_age(timestamp):
    if not timestamp:
        return "N/A"

    updated = datetime.fromtimestamp(timestamp)
    delta = datetime.now() - updated
    if delta.days > 0:
        return f"{delta.days}d ago"

    hours = int(delta.total_seconds() // 3600)
    if hours > 0:
        return f"{hours}h ago"

    minutes = max(0, int(delta.total_seconds() // 60))
    return f"{minutes}m ago"
