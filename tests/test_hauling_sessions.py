from app.hauling import (
    CONTRACT_STATE_DELIVERED,
    CONTRACT_STATE_LOADED,
    SESSION_STATUS_ARCHIVED,
    SESSION_STATUS_COMPLETED,
    HaulingContract,
    build_manifest,
)
from conftest import isolated_database, reload_module


def sample_contracts():
    return (
        HaulingContract(
            id="contract-a",
            pickup="Checkmate",
            delivery="Teasa Spaceport",
            commodity="Gold",
            scu=32,
            source_text="Raw source text should not be stored.",
            confidence=1.0,
            status="parsed",
            state=CONTRACT_STATE_LOADED,
            warnings=("Needs review.",),
        ),
        HaulingContract(
            id="contract-b",
            pickup="Checkmate",
            delivery="Lorville",
            commodity="Medical Supplies",
            scu=12,
            confidence=0.8,
            status="needs_review",
            state=CONTRACT_STATE_DELIVERED,
        ),
    )


def test_hauling_session_save_and_load_restores_manifest(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    storage = reload_module("app.hauling.storage")
    manifest = build_manifest(sample_contracts(), selected_ship="Railen")

    saved = storage.save_session("Railen Run", manifest)
    loaded = storage.load_session(saved.id)

    assert saved.id
    assert loaded.name == "Railen Run"
    assert loaded.selected_ship == "Railen"
    assert loaded.manifest.ship_capacity_scu == 640
    assert loaded.manifest.total_scu == 44
    assert loaded.manifest.loaded_scu == 44
    assert loaded.manifest.delivered_scu == 12
    contracts_by_id = {contract.id: contract for contract in loaded.manifest.contracts}
    assert contracts_by_id["contract-a"].state == CONTRACT_STATE_LOADED
    assert contracts_by_id["contract-b"].state == CONTRACT_STATE_DELIVERED
    assert contracts_by_id["contract-a"].source_text == ""
    assert "Needs review." in contracts_by_id["contract-a"].warnings


def test_hauling_session_update_replaces_contract_state(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    storage = reload_module("app.hauling.storage")
    manifest = build_manifest(sample_contracts(), selected_ship="Railen")
    saved = storage.save_session("Railen Run", manifest)
    updated_contracts = (
        HaulingContract(id="contract-a", pickup="Checkmate", delivery="Teasa Spaceport", commodity="Gold", scu=32),
    )

    updated = storage.save_session(
        "Updated Run",
        build_manifest(updated_contracts, selected_ship="C2 Hercules"),
        session_id=saved.id,
    )
    loaded = storage.load_session(saved.id)

    assert updated.id == saved.id
    assert loaded.name == "Updated Run"
    assert loaded.selected_ship == "C2 Hercules"
    assert len(loaded.manifest.contracts) == 1
    assert loaded.manifest.contracts[0].state == "planned"
    assert len(storage.list_sessions()) == 1


def test_hauling_session_archive_and_delete_are_local_to_hauling(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    storage = reload_module("app.hauling.storage")
    database.save_note("Saminus", "tag", "player note")
    saved = storage.save_session("Archive Me", build_manifest(sample_contracts(), selected_ship="Railen"))

    assert storage.archive_session(saved.id) == 1
    archived = storage.load_session(saved.id)
    assert archived.status == SESSION_STATUS_ARCHIVED

    assert storage.delete_session(saved.id) == 1
    assert storage.load_session(saved.id) is None
    assert database.get_note("Saminus") == ("tag", "player note")


def test_hauling_session_completed_status(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    storage = reload_module("app.hauling.storage")
    contracts = (
        HaulingContract(
            id="contract-a",
            pickup="Checkmate",
            delivery="Teasa Spaceport",
            commodity="Gold",
            scu=32,
            state=CONTRACT_STATE_DELIVERED,
        ),
    )

    saved = storage.save_session("Completed", build_manifest(contracts, selected_ship="Railen"))

    assert saved.status == SESSION_STATUS_COMPLETED
    assert saved.completed_at


def test_hauling_tables_created_during_database_init(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)

    with database.get_connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        columns = {row[1] for row in conn.execute("PRAGMA table_info(hauling_contracts)")}

    assert "hauling_sessions" in tables
    assert "hauling_contracts" in tables
    assert "source_text_hash" in columns
    assert "source_text" not in columns


def test_hauling_storage_does_not_persist_raw_source_text(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    storage = reload_module("app.hauling.storage")
    manifest = build_manifest(sample_contracts(), selected_ship="Railen")

    saved = storage.save_session("Privacy", manifest)

    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT source_text_hash FROM hauling_contracts WHERE session_id = ? AND contract_id = ?",
            (saved.id, "contract-a"),
        ).fetchone()

    assert row[0]
    assert row[0] != "Raw source text should not be stored."
