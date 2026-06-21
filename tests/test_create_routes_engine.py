from app.gui.trading.create_routes_engine import (
    DEFAULT_LOCATION_TYPES,
    DEFAULT_SYSTEMS,
    CreateRoutesSettings,
    generate_create_routes,
)
from app.trading_data import TradingOpportunity


def opportunity(commodity, buy_location, sell_location, profit_per_scu, buy_price=100):
    return TradingOpportunity(
        commodity=commodity,
        buy_location=buy_location,
        buy_price=buy_price,
        sell_location=sell_location,
        sell_price=buy_price + profit_per_scu,
        profit_per_scu=profit_per_scu,
        source="UEX",
        date_modified=100,
    )


def settings(**overrides):
    values = {
        "cargo_scu": 10,
        "max_investment": None,
        "systems": DEFAULT_SYSTEMS,
        "location_types": DEFAULT_LOCATION_TYPES,
        "avoid_dangerous": True,
        "avoid_hidden": True,
        "avoid_non_armistice": True,
        "allow_pyro": False,
        "allow_contested": False,
        "include_illegal": False,
        "legal_goods": True,
        "stable_routes": True,
        "high_profit": True,
        "allow_high_volatility": False,
        "include_mission_goods": False,
        "optimization_mode": "Highest Profit",
        "top_count": 2,
    }
    values.update(overrides)
    return CreateRoutesSettings(**values)


def test_generate_create_routes_accepts_snapshot_tuple_and_ranks_results():
    opportunities = (
        opportunity("Gold", "Stanton - Area18 - TDD", "Stanton - Orison - TDD", 600),
        opportunity("Laranite", "Stanton - Area18 - TDD", "Stanton - Orison - TDD", 900),
    )

    results = generate_create_routes(opportunities, settings())

    assert [result.opportunity.commodity for result in results] == ["Laranite", "Gold"]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].estimate.estimated_total_profit == 9_000


def test_generate_create_routes_filters_to_top_count():
    opportunities = (
        opportunity("Gold", "Stanton - Area18 - TDD", "Stanton - Orison - TDD", 600),
        opportunity("Laranite", "Stanton - Area18 - TDD", "Stanton - Orison - TDD", 900),
    )

    results = generate_create_routes(opportunities, settings(top_count=1))

    assert len(results) == 1
    assert results[0].opportunity.commodity == "Laranite"
