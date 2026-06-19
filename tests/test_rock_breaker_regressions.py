import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.gui.mining.mining_tab import MiningTab


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def mining_tab(qapp):
    tab = MiningTab()
    yield tab
    tab.refinery_timer.stop()
    tab.close()


@pytest.mark.parametrize(
    ("raw_value", "normalized", "multiplier"),
    [
        ("0", 0.0, 1.0),
        ("0.01", 0.01, 1.01),
        ("0.1", 0.1, 1.1),
        ("0.10", 0.1, 1.1),
        ("2", 0.02, 1.02),
        ("10", 0.10, 1.1),
        ("25", 0.25, 1.25),
    ],
)
def test_rock_resistance_is_offset_multiplier(mining_tab, raw_value, normalized, multiplier):
    resistance = mining_tab.normalize_rock_resistance(mining_tab.parse_float(raw_value))

    assert resistance == pytest.approx(normalized)
    assert mining_tab.rock_resistance_multiplier(resistance) == pytest.approx(multiplier)
    assert mining_tab.calculate_rock_required_power(10000, resistance, 1.5) == pytest.approx(
        10000 * multiplier * 1.5
    )


def test_zero_resistance_does_not_zero_power_needed(mining_tab):
    laser = SimpleNamespace(
        name="Test Laser",
        size=1,
        module_slots=0,
        min_power=5000,
        max_power=15000,
        resistance_factor=1.0,
        instability_factor=1.0,
        optimal_charge_rate=1.0,
        optimal_charge_window=1.0,
    )

    setup = mining_tab.evaluate_rock_setup(
        laser=laser,
        modules=(),
        gadget=None,
        mass=10000,
        resistance=0.0,
        instability=1.0,
    )

    assert setup["power_window"].startswith("Need 10,000 /")
    assert setup["risk"] != "Overpowered"


def test_higher_resistance_increases_required_power(mining_tab):
    base = mining_tab.calculate_rock_required_power(10000, 0.0, 1.0)
    low = mining_tab.calculate_rock_required_power(10000, 0.01, 1.0)
    high = mining_tab.calculate_rock_required_power(10000, 0.25, 1.0)

    assert base == 10000
    assert base < low < high
