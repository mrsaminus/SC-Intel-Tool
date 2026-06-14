from app.gui.trading.route_quality import calculate_route_quality
from app.gui.trading.route_summary import format_number, format_route_summary, notes_from_flags
from app.trading_storage import TradingRouteRecord


def test_route_quality_rewards_profitable_full_affordable_routes():
    quality = calculate_route_quality(
        total_profit=1_250_000,
        profit_per_scu=1_500,
        full_cargo=True,
        affordable=True,
    )

    assert quality.label == "Excellent"
    assert "Full cargo" in quality.flags


def test_route_quality_flags_suspicious_routes():
    quality = calculate_route_quality(
        total_profit=2_000_000,
        profit_per_scu=5_000,
        full_cargo=False,
        affordable=False,
        suspicious=True,
    )

    assert "Investment limited" in quality.flags
    assert "Not affordable" in quality.flags
    assert "High margin / possible outlier" in quality.flags


def test_route_summary_format_is_discord_friendly():
    record = TradingRouteRecord(
        source="UEX",
        commodity="Gold",
        buy_location="Area18 TDD",
        sell_location="Orison TDD",
        buy_price=7500,
        sell_price=8100,
        profit_per_scu=600,
        cargo_scu=696,
        buy_cost=5_220_000,
        total_profit=417_600,
        quality="Good",
    )

    summary = format_route_summary(record)

    assert "Commodity: Gold" in summary
    assert "Buy from: Area18 TDD @ 7,500 aUEC / SCU" in summary
    assert "Estimated total profit: 417,600 aUEC" in summary


def test_format_helpers_handle_invalid_values_cleanly():
    assert format_number("not a number") == "N/A"
    assert notes_from_flags((), ()) == "None"
    assert notes_from_flags(("Full cargo",), ("UEX",)) == "Full cargo, UEX"
