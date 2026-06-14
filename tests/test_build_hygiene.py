from pathlib import Path


def test_windows_build_script_bundles_public_mining_data_not_reference_material():
    script = Path("scripts/build_windows.ps1").read_text(encoding="utf-8")

    assert "intentionally not bundling it in public release builds" in script
    assert "app\\assets\\mining_public" in script
    assert ";app/assets/mining_public" in script
    assert "--add-data\", \"$Reference" not in script
