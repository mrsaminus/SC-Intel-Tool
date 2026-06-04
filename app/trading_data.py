from dataclasses import dataclass
from datetime import datetime
from math import floor

from app.uex_client import fetch_all_commodity_prices


UNITS_PER_SCU = 100


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


@dataclass(frozen=True)
class TradingEstimate:
    units_per_scu: int
    cargo_scu: float
    units_capacity: int
    effective_units: int
    effective_cargo_scu: float
    estimated_buy_cost: float
    estimated_total_profit: float
    profit_per_scu: float
    investment_limited: bool


def fetch_trading_opportunities(include_unprofitable=False):
    prices = fetch_all_commodity_prices()
    return build_trading_opportunities(prices, include_unprofitable=include_unprofitable), len(prices)


def calculate_trade_estimate(opportunity, cargo_scu, max_investment=None, units_per_scu=UNITS_PER_SCU):
    safe_cargo_scu = max(0, cargo_scu or 0)
    units_capacity = floor(safe_cargo_scu * units_per_scu)

    investment_units = units_capacity
    if max_investment is not None:
        safe_investment = max(0, max_investment)
        if opportunity.buy_price > 0:
            investment_units = floor(safe_investment / opportunity.buy_price)
        else:
            investment_units = 0

    effective_units = max(0, min(units_capacity, investment_units))
    effective_cargo_scu = effective_units / units_per_scu if units_per_scu else 0
    estimated_buy_cost = opportunity.buy_price * effective_units
    estimated_total_profit = opportunity.profit_per_unit * effective_units
    profit_per_scu = opportunity.profit_per_unit * units_per_scu
    investment_limited = max_investment is not None and investment_units < units_capacity

    return TradingEstimate(
        units_per_scu=units_per_scu,
        cargo_scu=safe_cargo_scu,
        units_capacity=units_capacity,
        effective_units=effective_units,
        effective_cargo_scu=effective_cargo_scu,
        estimated_buy_cost=estimated_buy_cost,
        estimated_total_profit=estimated_total_profit,
        profit_per_scu=profit_per_scu,
        investment_limited=investment_limited,
    )


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
