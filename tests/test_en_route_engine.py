from app.trading_en_route import (
    build_uex_en_route_opportunities,
    commodity_display_values,
    location_display_values,
    location_matches,
)
from app.uex_client import UEXCommodityPrice


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


def build(prices, **filters):
    return build_uex_en_route_opportunities(
        prices,
        origin=filters.pop("origin", "Stanton - Area18 - TDD"),
        destination=filters.pop("destination", "Stanton - Orison - TDD"),
        cargo_scu=filters.pop("cargo_scu", 10),
        **filters,
    )


def test_exact_origin_destination_profitable_route():
    result = build([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
    ])

    assert len(result.routes) == 1
    route = result.routes[0]
    assert route.commodity == "Gold"
    assert route.profit_per_scu == 600
    assert route.cargo_scu == 10
    assert route.buy_cost == 75_000
    assert route.total_profit == 6_000
    assert round(route.margin_percent, 2) == 8.0


def test_no_matching_sell_location_reports_destination_data_gap():
    result = build([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Lorville"),
    ])

    assert result.routes == []
    assert result.destination_has_data is False
    assert "destination" in result.message.lower()


def test_no_matching_buy_location_reports_origin_data_gap():
    result = build([
        price("Gold", buy=7500, location="Lorville"),
        price("Gold", sell=8100, location="Orison"),
    ])

    assert result.routes == []
    assert result.origin_has_data is False
    assert "origin" in result.message.lower()


def test_unprofitable_route_excluded_by_default():
    result = build([
        price("Gold", buy=8500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
    ])

    assert result.routes == []


def test_budget_limits_cargo_with_flooring():
    result = build(
        [
            price("Gold", buy=7500, location="Area18"),
            price("Gold", sell=8100, location="Orison"),
        ],
        cargo_scu=10,
        max_investment=20_000,
    )

    route = result.routes[0]
    assert route.cargo_scu == 2
    assert route.buy_cost == 15_000
    assert route.total_profit == 1_200
    assert "Budget limited" in route.notes


def test_zero_or_empty_budget_uses_full_cargo_when_not_provided():
    prices = [
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
    ]

    without_budget = build(prices, cargo_scu=10, max_investment=None).routes[0]
    with_zero_budget = build(prices, cargo_scu=10, max_investment=0).routes[0]

    assert without_budget.cargo_scu == 10
    assert with_zero_budget.cargo_scu == 10


def test_zero_buy_price_excluded():
    result = build([
        price("Gold", buy=0, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
    ])

    assert result.routes == []
    assert result.buy_row_count == 0


def test_duplicate_commodity_location_rows_use_best_valid_values():
    result = build([
        price("Gold", buy=7800, location="Area18"),
        price("Gold", buy=7400, location="Area18"),
        price("Gold", sell=8000, location="Orison"),
        price("Gold", sell=8300, location="Orison"),
    ])

    route = result.routes[0]
    assert route.buy_price == 7400
    assert route.sell_price == 8300
    assert route.profit_per_scu == 900


def test_location_name_normalization_supports_hierarchy_and_punctuation():
    row = price("Gold", buy=7500, system="Stanton", location="Area 18", terminal="TDD Admin")

    assert location_matches(row, "stanton > area-18 > tdd admin")
    assert location_matches(row, "Area18")
    assert location_matches(row, "TDD Admin")


def test_multiple_commodities_sorted_by_total_profit_then_profit_per_scu():
    result = build([
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
        price("Laranite", buy=1000, location="Area18"),
        price("Laranite", sell=2000, location="Orison"),
    ])

    assert [route.commodity for route in result.routes] == ["Laranite", "Gold"]


def test_display_helpers_use_uex_price_rows():
    prices = [
        price("Gold", buy=7500, location="Area18"),
        price("Laranite", sell=2000, location="Orison"),
    ]

    assert "Stanton - Area18 - TDD" in location_display_values(prices)
    assert commodity_display_values(prices) == ["Gold", "Laranite"]
