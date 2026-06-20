from app.trading_ship_cargo import (
    canonical_trading_ship_name,
    trading_ship_cargo_record,
    trading_ship_cargo_scu,
    trading_ship_names,
)


def test_railen_has_known_trading_cargo_capacity():
    assert canonical_trading_ship_name("Railen") == "Railen"
    assert canonical_trading_ship_name("Gatac Railen") == "Railen"
    assert trading_ship_cargo_scu("Railen") == 640
    assert trading_ship_cargo_scu("Gatac Railen") == 640
    assert "Railen" in trading_ship_names()

    record = trading_ship_cargo_record("Railen")
    assert record is not None
    assert record.manufacturer == "Gatac"
    assert record.cargo_scu == 640
