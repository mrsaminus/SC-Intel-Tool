from pathlib import Path

from app.mining_data import PUBLIC_MINING_ROOT, load_mining_data


EXPECTED_PUBLIC_FILES = (
    Path("Calculator") / "rock-breaking-calculator-data.json",
    Path("defaults") / "equipment_shops_cache_default.json",
    Path("assets") / "Mineral Stats" / "Mineral_Where.txt",
)


def test_public_mining_bundle_contains_only_expected_runtime_files():
    files = {
        path.relative_to(PUBLIC_MINING_ROOT)
        for path in PUBLIC_MINING_ROOT.rglob("*")
        if path.is_file()
    }

    assert files == set(EXPECTED_PUBLIC_FILES)


def test_mining_data_loads_from_public_bundle_when_reference_root_is_missing(tmp_path):
    data = load_mining_data(tmp_path / "missing_reference_root")

    assert data.errors == []
    assert len(data.locations) >= 250
    assert any(location.mineral == "Laranite" for location in data.locations)
    assert len(data.equipment) >= 50
    assert any(item.name.startswith("Lancet") for item in data.equipment)
    assert len(data.rock_lasers) > 0
    assert len(data.quality_bands) > 0
    assert len(data.scan_signatures) > 0
