import pytest

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from app.uex_client import UEXCommodityPrice
from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeReferenceService(QObject):
    loaded = Signal(object)
    error = Signal(object)
    state_changed = Signal(str)

    def __init__(self, data=None):
        super().__init__()
        self.data = data


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
        terminal_name=terminal,
        star_system_name=system,
        location_name=location,
        date_modified=updated,
    )


def sample_prices():
    return [
        price("Gold", buy=7500, location="Area18"),
        price("Gold", sell=8100, location="Orison"),
        price("Laranite", buy=1000, location="Area18"),
        price("Laranite", sell=2000, location="Lorville"),
    ]


def test_uex_price_cache_round_trip_and_reference_indexes(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    cache.save_uex_prices_cache(sample_prices())
    rows, metadata = cache.load_uex_prices_cache()

    assert metadata.cache_key == cache.UEX_PRICES_CACHE_KEY
    assert metadata.row_count == 4
    assert cache.cache_status(cache.UEX_PRICES_CACHE_KEY) == "fresh"
    assert [row.commodity_name for row in rows] == ["Gold", "Gold", "Laranite", "Laranite"]
    assert rows[1].price_sell == 8100

    with database.get_connection() as conn:
        commodity_count = conn.execute("SELECT COUNT(*) FROM cache_uex_commodities").fetchone()[0]
        location_count = conn.execute("SELECT COUNT(*) FROM cache_uex_locations").fetchone()[0]

    assert commodity_count == 2
    assert location_count == 3


def test_uex_loader_uses_fresh_cache_without_network(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    cache.save_uex_prices_cache(sample_prices())
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("fresh cache should not fetch UEX"),
    )

    snapshot = uex_client.load_all_commodity_prices()

    assert snapshot.from_cache
    assert snapshot.cache_status == "fresh"
    assert len(snapshot.prices) == 4


def test_uex_loader_uses_stale_cache_without_auto_refresh(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    cache.save_uex_prices_cache(sample_prices())
    cache.invalidate_cache(cache.UEX_PRICES_CACHE_KEY)
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("stale cache should not auto-refresh"),
    )

    snapshot = uex_client.load_all_commodity_prices()

    assert snapshot.from_cache
    assert snapshot.cache_status == "stale"
    assert len(snapshot.prices) == 4


def test_uex_loader_fetches_and_populates_cache_on_miss(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    calls = []
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: calls.append("fetch") or sample_prices(),
    )

    snapshot = uex_client.load_all_commodity_prices()
    cached_rows, metadata = cache.load_uex_prices_cache()

    assert calls == ["fetch"]
    assert not snapshot.from_cache
    assert len(snapshot.prices) == 4
    assert len(cached_rows) == 4
    assert metadata.row_count == 4


def test_manual_refresh_replaces_cached_uex_rows(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    cache.save_uex_prices_cache(sample_prices())
    fresh_prices = [price("Diamond", buy=100, location="Area18"), price("Diamond", sell=200, location="Orison")]
    monkeypatch.setattr(uex_client, "fetch_all_commodity_prices", lambda: fresh_prices)

    snapshot = uex_client.load_all_commodity_prices(force_refresh=True)
    cached_rows, metadata = cache.load_uex_prices_cache()

    assert not snapshot.from_cache
    assert [row.commodity_name for row in cached_rows] == ["Diamond", "Diamond"]
    assert metadata.row_count == 2


def test_uex_unavailable_uses_existing_cache(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    uex_client = reload_module("app.uex_client")
    cache.save_uex_prices_cache(sample_prices())
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: (_ for _ in ()).throw(RuntimeError("UEX unavailable")),
    )

    snapshot = uex_client.load_all_commodity_prices(force_refresh=True)

    assert snapshot.from_cache
    assert snapshot.cache_status == "offline"
    assert "UEX unavailable" in snapshot.source_error
    assert len(snapshot.prices) == 4


def test_uex_unavailable_without_cache_raises(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: (_ for _ in ()).throw(RuntimeError("UEX unavailable")),
    )

    with pytest.raises(RuntimeError):
        uex_client.load_all_commodity_prices()


def test_trading_opportunities_rebuild_from_cached_uex_rows(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_uex_prices_cache(sample_prices())
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("cached Trading opportunities should not fetch UEX"),
    )
    trading_data = reload_module("app.trading_data")

    routes, row_count = trading_data.fetch_trading_opportunities(include_unprofitable=False)

    assert row_count == 4
    assert any(route.commodity == "Gold" and route.profit_per_scu == 600 for route in routes)
    assert any(route.commodity == "Laranite" and route.profit_per_scu == 1000 for route in routes)


def test_best_buyer_rebuilds_from_cached_uex_rows(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_uex_prices_cache(sample_prices())
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("cached Best Buyer should not fetch UEX"),
    )
    best_buyer = reload_module("app.trading_best_buyer")

    buyers, row_count = best_buyer.fetch_uex_best_buyers("Gold", quantity_scu=24)

    assert row_count == 4
    assert len(buyers) == 1
    assert buyers[0].location == "Stanton - Orison - TDD"
    assert buyers[0].quantity_scu == 24


def test_en_route_rebuilds_from_cached_uex_rows(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_uex_prices_cache(sample_prices())
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("cached En Route should not fetch UEX"),
    )
    en_route = reload_module("app.trading_en_route")

    result = en_route.fetch_uex_en_route_opportunities(
        origin="Stanton - Area18 - TDD",
        destination="Stanton - Orison - TDD",
        cargo_scu=10,
    )

    assert result.price_row_count == 4
    assert len(result.routes) == 1
    assert result.routes[0].commodity == "Gold"


def test_reference_data_rebuilds_commodities_and_shops_from_cache(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_uex_prices_cache(sample_prices())
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("cached reference data should not fetch UEX"),
    )
    reference_data = reload_module("app.gui.trading.reference_data")

    data = reference_data.load_trading_reference_data()

    assert data.cache_status == "fresh"
    assert [commodity.name for commodity in data.commodities] == ["Gold", "Laranite"]
    assert any(shop.name == "Stanton - Orison - TDD" for shop in data.shops)
    assert len(data.price_rows) == 4


def test_trade_routes_tab_builds_routes_from_cached_reference_rows(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    reference_data = reload_module("app.gui.trading.reference_data")
    trade_routes = reload_module("app.gui.trading.trade_routes_tab")
    uex_client = reload_module("app.uex_client")
    monkeypatch.setattr(
        uex_client,
        "fetch_all_commodity_prices",
        lambda: pytest.fail("Trade Routes should reuse cached reference rows"),
    )
    data = reference_data.TradingReferenceData(
        commodities=(),
        commodity_types=(),
        locations=(),
        shops=(),
        ships=(),
        price_rows=tuple(sample_prices()),
    )

    tab = trade_routes.TradeRoutesTab(FakeReferenceService(data))
    routes, row_count = tab.load_trade_routes()

    assert row_count == 4
    assert any(route.commodity == "Gold" and route.profit_per_scu == 600 for route in routes)


def test_create_routes_tab_builds_opportunities_from_cached_reference_rows(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    reference_data = reload_module("app.gui.trading.reference_data")
    create_routes = reload_module("app.gui.trading.create_routes_tab")
    data = reference_data.TradingReferenceData(
        commodities=(),
        commodity_types=(),
        locations=(),
        shops=(),
        ships=(),
        price_rows=tuple(sample_prices()),
        cache_status="fresh",
    )

    tab = create_routes.CreateRoutesTab(FakeReferenceService(data))
    tab.on_reference_loaded(data)

    assert tab.price_row_count == 4
    assert any(route.commodity == "Gold" and route.profit_per_scu == 600 for route in tab.all_opportunities)
