from dataclasses import dataclass

from PySide6.QtWidgets import QApplication


QUALITY_SORT = {
    "Excellent": 4,
    "Good": 3,
    "Fair": 2,
    "Low": 1,
    "N/A": 0,
}


@dataclass(frozen=True)
class RouteQuality:
    label: str
    sort_value: int
    flags: tuple[str, ...]


def calculate_route_quality(
    *,
    total_profit=None,
    profit_per_scu=None,
    profit_per_minute=None,
    full_cargo=None,
    affordable=None,
    suspicious=False,
    has_profit=True,
):
    if not has_profit:
        return RouteQuality("N/A", QUALITY_SORT["N/A"], tuple())

    score = 0
    flags = []

    total_profit = safe_float(total_profit)
    profit_per_scu = safe_float(profit_per_scu)
    profit_per_minute = safe_float(profit_per_minute)

    if total_profit is not None:
        if total_profit >= 1_000_000:
            score += 3
        elif total_profit >= 250_000:
            score += 2
        elif total_profit > 0:
            score += 1

    if profit_per_scu is not None:
        if profit_per_scu >= 1_000:
            score += 3
        elif profit_per_scu >= 250:
            score += 2
        elif profit_per_scu > 0:
            score += 1
    elif profit_per_minute is not None:
        if profit_per_minute >= 25_000:
            score += 3
        elif profit_per_minute >= 5_000:
            score += 2
        elif profit_per_minute > 0:
            score += 1

    if full_cargo is True:
        score += 1
        flags.append("Full cargo")
    elif full_cargo is False:
        flags.append("Investment limited")

    if affordable is True:
        score += 1
    elif affordable is False:
        flags.append("Not affordable")

    if suspicious:
        score -= 3
        flags.append("High margin / possible outlier")

    if not any_positive(total_profit, profit_per_scu, profit_per_minute):
        label = "Low"
    elif score >= 6:
        label = "Excellent"
    elif score >= 4:
        label = "Good"
    elif score >= 2:
        label = "Fair"
    else:
        label = "Low"

    return RouteQuality(label, QUALITY_SORT[label], tuple(flags))


def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def any_positive(*values):
    return any(value is not None and value > 0 for value in values)


def copy_to_clipboard(text):
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text or "")
