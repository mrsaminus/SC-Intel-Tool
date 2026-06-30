import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.blueprints_client import BlueprintIngredient, BlueprintMission, BlueprintRecord
from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def sample_blueprint(key="bp-1", name="Test Blueprint"):
    return BlueprintRecord(
        key=key,
        blueprint_name=name,
        crafted_item=name,
        category="Field Recon",
        ownable=True,
        craft_time_seconds=360,
        ingredients=(
            BlueprintIngredient(
                slot="Core",
                name="Test Alloy",
                quantity=2.5,
                unit="scu",
                min_quality=0.75,
                quality_effects=("Durability: 1 -> 2 multiplier",),
            ),
            BlueprintIngredient(
                slot="Catalyst",
                name="Signal Matrix",
                quantity=1,
                unit="unit",
                min_quality=None,
                quality_effects=(),
            ),
        ),
        missions=(
            BlueprintMission(
                name="Claim Blueprint",
                drop_chance="5%",
                mission_id="mission-1",
                contractor="Covalex",
                reputation_giver="Civilian Defense Force",
                reputation_rank="Junior",
                location="Orison",
                system="Stanton",
            ),
        ),
        patch="4.2",
        source="SC Craft Tools",
        source_url="https://example.invalid/blueprints",
        raw={"blueprint_id": key, "name": name, "category": "Field Recon"},
    )


def test_blueprint_cache_round_trip_preserves_recipes_and_missions(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")

    cache.save_blueprint_cache([sample_blueprint()])
    blueprints, metadata = cache.load_blueprint_cache()

    assert metadata.cache_key == cache.BLUEPRINT_CACHE_KEY
    assert metadata.row_count == 1
    assert cache.cache_status(cache.BLUEPRINT_CACHE_KEY) == "fresh"
    assert len(blueprints) == 1
    blueprint = blueprints[0]
    assert blueprint.blueprint_name == "Test Blueprint"
    assert blueprint.category == "Field Recon"
    assert blueprint.ingredients[0].name == "Test Alloy"
    assert blueprint.ingredients[0].quantity == 2.5
    assert blueprint.ingredients[0].quality_effects == ("Durability: 1 -> 2 multiplier",)
    assert blueprint.missions[0].name == "Claim Blueprint"
    assert blueprint.missions[0].drop_chance == "5%"
    assert blueprint.missions[0].contractor == "Covalex"
    assert blueprint.raw["blueprint_id"] == "bp-1"


def test_blueprint_loader_uses_fresh_cache_without_network(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    cache.save_blueprint_cache([sample_blueprint()])
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: pytest.fail("fresh blueprint cache should not fetch live source"),
    )

    snapshot = blueprints_client.load_blueprints()

    assert snapshot.from_cache
    assert snapshot.cache_status == "fresh"
    assert snapshot.blueprints[0].blueprint_name == "Test Blueprint"


def test_blueprint_loader_uses_stale_cache_without_auto_refresh(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    cache.save_blueprint_cache([sample_blueprint()])
    cache.invalidate_cache(cache.BLUEPRINT_CACHE_KEY)
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: pytest.fail("stale blueprint cache should not auto-refresh"),
    )

    snapshot = blueprints_client.load_blueprints()

    assert snapshot.from_cache
    assert snapshot.cache_status == "stale"
    assert len(snapshot.blueprints) == 1


def test_blueprint_loader_fetches_and_populates_cache_on_miss(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: [sample_blueprint(key="bp-live", name="Live Blueprint")],
    )

    snapshot = blueprints_client.load_blueprints()
    cached_blueprints, metadata = cache.load_blueprint_cache()

    assert not snapshot.from_cache
    assert snapshot.cache_status == "fresh"
    assert cached_blueprints[0].key == "bp-live"
    assert metadata.row_count == 1


def test_blueprint_manual_refresh_replaces_cache(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    cache.save_blueprint_cache([sample_blueprint(key="old", name="Old Blueprint")])
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: [sample_blueprint(key="new", name="New Blueprint")],
    )

    snapshot = blueprints_client.load_blueprints(force_refresh=True)
    cached_blueprints, _metadata = cache.load_blueprint_cache()

    assert not snapshot.from_cache
    assert [blueprint.key for blueprint in cached_blueprints] == ["new"]


def test_blueprint_loader_uses_cache_when_source_unavailable(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    blueprints_client = reload_module("app.blueprints_client")
    cache.save_blueprint_cache([sample_blueprint()])
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: (_ for _ in ()).throw(RuntimeError("blueprint source unavailable")),
    )

    snapshot = blueprints_client.load_blueprints(force_refresh=True)

    assert snapshot.from_cache
    assert snapshot.cache_status == "offline"
    assert "blueprint source unavailable" in snapshot.source_error
    assert snapshot.blueprints[0].key == "bp-1"


def test_blueprint_loader_raises_when_source_unavailable_without_cache(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    blueprints_client = reload_module("app.blueprints_client")
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: (_ for _ in ()).throw(RuntimeError("blueprint source unavailable")),
    )

    with pytest.raises(RuntimeError):
        blueprints_client.load_blueprints()


def test_clear_blueprint_cache_preserves_owned_blueprint_state(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    storage = reload_module("app.blueprints_storage")
    cache.save_blueprint_cache([sample_blueprint()])
    storage.set_blueprint_owned("bp-1", "Test Blueprint", "SC Craft Tools", True)

    cache.clear_cache_key(cache.BLUEPRINT_CACHE_KEY)

    cached_blueprints, metadata = cache.load_blueprint_cache()
    assert cached_blueprints == []
    assert metadata is None
    assert storage.get_owned_blueprint_keys() == {"bp-1"}


def test_blueprint_browser_first_open_loads_cached_blueprints(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    cache = reload_module("app.local_cache")
    cache.save_blueprint_cache([sample_blueprint()])
    blueprints_client = reload_module("app.blueprints_client")
    monkeypatch.setattr(
        blueprints_client,
        "fetch_blueprints",
        lambda: pytest.fail("Blueprint Browser first open should use cache"),
    )
    browser_module = reload_module("app.gui.bp_overview.blueprint_browser_tab")

    tab = browser_module.BlueprintBrowserTab()
    tab.ensure_initial_load()
    deadline = time.time() + 5
    while tab.refresh_running and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.02)
    qapp.processEvents()

    assert not tab.refresh_running
    assert len(tab.blueprints) == 1
    assert "cached" in tab.status_label.text().lower()
    assert tab.blueprint_table.rowCount() == 1
    tab.close()
