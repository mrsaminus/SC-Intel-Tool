from pathlib import Path

from app.trading_data import build_trading_opportunities
from app.trading_trade_routes import filter_trade_routes
from app.uex_client import UEXCommodityPrice


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT_FILES = [
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "CHANGELOG.md",
    ROOT / "docs" / "alpha_tester_checklist.md",
    ROOT / "docs" / "beta_readiness_checklist.md",
    ROOT / "docs" / "trading_data_sources.md",
]
PUBLIC_CODE_DIRS = [
    ROOT / "app" / "gui" / "trading",
    ROOT / "app" / "gui" / "settings_tab.py",
]


def price(
    commodity,
    buy=None,
    sell=None,
    system="Stanton",
    location="Area18",
    terminal="TDD",
    updated=100,
):
    return UEXCommodityPrice(
        commodity_name=commodity,
        price_buy=buy,
        price_sell=sell,
        star_system_name=system,
        location_name=location,
        terminal_name=terminal,
        date_modified=updated,
    )


def test_trade_routes_use_uex_buy_sell_opportunities():
    routes = build_trading_opportunities([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
        price("Laranite", buy=1000, location="Area18"),
        price("Laranite", sell=2000, location="Lorville"),
    ])

    assert {route.source for route in routes} == {"UEX"}
    assert any(route.commodity == "Gold" and route.profit_per_scu == 600 for route in routes)
    assert any(route.commodity == "Laranite" and route.profit_per_scu == 1000 for route in routes)


def test_trade_route_filters_match_origin_destination_and_commodity():
    routes = build_trading_opportunities([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
        price("Gold", sell=8200, location="Lorville"),
        price("Laranite", buy=1000, location="Area18"),
        price("Laranite", sell=2000, location="Orison"),
    ])

    filtered = filter_trade_routes(
        routes,
        origin="Area18",
        destination="Orison",
        commodity="Gold",
    )

    assert len(filtered) == 1
    assert filtered[0].commodity == "Gold"
    assert "Area18" in filtered[0].buy_location
    assert "Orison" in filtered[0].sell_location


def test_trade_route_filters_return_empty_for_no_results():
    routes = build_trading_opportunities([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
    ])

    assert filter_trade_routes(routes, destination="New Babbage") == []


def test_public_trading_text_does_not_expose_old_tooling():
    banned = (
        "SC " + "Trade Tools",
        "sc-" + "trade.tools",
        "SC-" + "Trading.tools",
        "advanced SC " + "Trade Tools workflow",
        "unavailable in " + "the public build",
    )
    paths = []
    for entry in PUBLIC_CODE_DIRS:
        if entry.is_dir():
            paths.extend(entry.glob("*.py"))
        else:
            paths.append(entry)
    paths.extend(PUBLIC_TEXT_FILES)

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for phrase in banned:
            assert phrase not in text, f"{phrase!r} leaked in {path}"
