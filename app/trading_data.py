from dataclasses import dataclass
from datetime import datetime

from app.uex_client import load_all_commodity_prices


SUSPICIOUS_MARGIN_RATIO = 25


@dataclass(frozen=True)
class TradingOpportunity:
    commodity: str
    buy_location: str
    buy_price: float
    sell_location: str
    sell_price: float
    profit_per_scu: float
    source: str
    date_modified: int | None


@dataclass(frozen=True)
class TradingEstimate:
    cargo_scu: float
    effective_cargo_scu: float
    estimated_buy_cost: float
    estimated_total_profit: float
    investment_limited: bool
    full_cargo_affordable: bool


def fetch_trading_opportunities(include_unprofitable=False, force_refresh=False):
    prices = load_all_commodity_prices(force_refresh=force_refresh).prices
    return build_trading_opportunities(prices, include_unprofitable=include_unprofitable), len(prices)


def calculate_trade_estimate(opportunity, cargo_scu, max_investment=None):
    safe_cargo_scu = max(0, cargo_scu or 0)
    full_cargo_buy_cost = opportunity.buy_price * safe_cargo_scu
    effective_cargo_scu = safe_cargo_scu
    if max_investment is not None:
        safe_investment = max(0, max_investment)
        if opportunity.buy_price > 0:
            effective_cargo_scu = min(safe_cargo_scu, safe_investment / opportunity.buy_price)
        else:
            effective_cargo_scu = 0

    effective_cargo_scu = max(0, effective_cargo_scu)
    estimated_buy_cost = opportunity.buy_price * effective_cargo_scu
    estimated_total_profit = opportunity.profit_per_scu * effective_cargo_scu
    investment_limited = max_investment is not None and effective_cargo_scu < safe_cargo_scu
    full_cargo_affordable = max_investment is None or full_cargo_buy_cost <= max(0, max_investment)

    return TradingEstimate(
        cargo_scu=safe_cargo_scu,
        effective_cargo_scu=effective_cargo_scu,
        estimated_buy_cost=estimated_buy_cost,
        estimated_total_profit=estimated_total_profit,
        investment_limited=investment_limited,
        full_cargo_affordable=full_cargo_affordable,
    )


def is_suspicious_margin(opportunity, margin_ratio=SUSPICIOUS_MARGIN_RATIO):
    if opportunity.buy_price <= 0:
        return True

    return opportunity.sell_price / opportunity.buy_price > margin_ratio


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
                    profit_per_scu=profit,
                    source="UEX",
                    date_modified=max_date_modified(buy_row.date_modified, sell_row.date_modified),
                ))

    opportunities.sort(
        key=lambda opportunity: (
            -opportunity.profit_per_scu,
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
