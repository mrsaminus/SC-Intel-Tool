from app.trading_best_buyer import build_best_buyers
from app.uex_client import UEXCommodityPrice


def price(
    commodity,
    sell=None,
    system="Stanton",
    location="Area18",
    terminal="TDD",
    updated=100,
):
    return UEXCommodityPrice(
        commodity_name=commodity,
        price_buy=None,
        price_sell=sell,
        star_system_name=system,
        location_name=location,
        terminal_name=terminal,
        date_modified=updated,
    )


def test_best_buyer_ranks_highest_sell_price_first():
    buyers = build_best_buyers([
        price("Gold", sell=8000, location="Area18"),
        price("Gold", sell=8500, location="Orison"),
        price("Gold", sell=8100, location="Lorville"),
    ], "Gold", quantity_scu=24)

    assert [buyer.location for buyer in buyers] == [
        "Stanton - Orison - TDD",
        "Stanton - Lorville - TDD",
        "Stanton - Area18 - TDD",
    ]
    assert buyers[0].quantity_scu == 24
    assert buyers[0].source == "UEX"


def test_best_buyer_deduplicates_locations_by_best_sell_price():
    buyers = build_best_buyers([
        price("Gold", sell=8000, location="Area18", terminal="TDD"),
        price("Gold", sell=8300, location="Area18", terminal="TDD"),
        price("Gold", sell=7900, location="Area18", terminal="TDD"),
    ], "gold")

    assert len(buyers) == 1
    assert buyers[0].sell_price == 8300


def test_best_buyer_ignores_missing_or_zero_sell_prices():
    buyers = build_best_buyers([
        price("Gold", sell=None, location="Area18"),
        price("Gold", sell=0, location="Lorville"),
        price("Gold", sell=8100, location="Orison"),
        price("Laranite", sell=9000, location="Area18"),
    ], "Gold")

    assert len(buyers) == 1
    assert buyers[0].location == "Stanton - Orison - TDD"


def test_best_buyer_returns_empty_for_unavailable_commodity_data():
    assert build_best_buyers([price("Gold", sell=8000)], "Diamond") == []

