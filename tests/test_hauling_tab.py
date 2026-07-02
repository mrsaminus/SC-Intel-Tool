import os

import pytest
from PySide6.QtWidgets import QApplication

from app.hauling import CONTRACT_STATE_DELIVERED, CONTRACT_STATE_LOADED, CONTRACT_STATE_PLANNED
from app.ocr.results import OCRPipelineResult, OCRResult
from conftest import isolated_database, reload_module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def build_tab(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    module = reload_module("app.gui.hauling_tab")
    return module.HaulingTab()


def run_ocr_synchronously(worker, on_result=None, on_error=None, on_finished=None):
    try:
        if on_result:
            on_result(worker.function())
    except Exception as exc:
        if on_error:
            on_error(exc)
        else:
            raise
    finally:
        if on_finished:
            on_finished()


class FakeOCRService:
    def __init__(self, text="", status="ok", message=""):
        self.text = text
        self.status = status
        self.message = message
        self.calls = []

    def scan_profile_region(self, profile, region, parser=None, capture_function=None):
        self.calls.append((profile, region, parser))
        if self.status != "ok":
            return OCRPipelineResult(
                status=self.status,
                ocr_result=OCRResult(text=self.text),
                message=self.message,
                errors=(self.message,) if self.message else (),
            )
        ocr_result = OCRResult(text=self.text)
        return OCRPipelineResult(
            status="ok",
            ocr_result=ocr_result,
            parsed_result=parser.parse(ocr_result) if parser else None,
        )


def sample_contract_text(quantity=32):
    return f"""
    Pick up: Checkmate
    Deliver to: Teasa Spaceport
    Commodity: Construction Materials
    Quantity: {quantity} SCU
    Reward: 12000 aUEC
    """


def save_hauling_region(tab):
    module = reload_module("app.gui.hauling_tab")
    profiles = reload_module("app.ocr.profiles")
    regions = reload_module("app.ocr.regions")
    tab.ocr_profile_manager.save_region(
        regions.OCRRegion.from_tuple(
            (10, 20, 300, 120),
            profile=profiles.HAULING_CONTRACTS_PROFILE_KEY,
            name=module.HAULING_REGION_NAME,
        )
    )


def select_first_contract(tab):
    tab.contracts_table.setCurrentCell(0, 0)


def test_hauling_tab_manual_parse_updates_manifest(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Railen")
    tab.contract_text.setPlainText(sample_contract_text())

    tab.parse_contracts()
    qapp.processEvents()

    assert len(tab.contracts) == 1
    assert tab.manifest.selected_ship == "Railen"
    assert tab.manifest.ship_capacity_scu == 640
    assert tab.manifest.total_scu == 32
    assert tab.manifest.loaded_scu == 0
    assert tab.manifest.remaining_scu == 640
    assert tab.manifest.planned_contracts == 1
    assert tab.contracts_table.rowCount() == 1
    assert tab.contracts_table.item(0, 0).text() == "Planned"
    assert tab.contracts_table.item(0, 1).text() == "Checkmate"
    assert tab.contracts_table.item(0, 2).text() == "Teasa Spaceport"
    assert tab.dashboard_labels["loaded_scu"].text() == "0 SCU"
    assert tab.dashboard_labels["remaining_capacity"].text() == "640 SCU"
    assert "Parsed 1 contract candidate" in tab.status_label.text()
    tab.close()


def test_hauling_tab_ship_selection_recalculates_remaining_scu(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.contract_text.setPlainText(sample_contract_text(quantity=500))
    tab.parse_contracts()

    tab.ship_combo.setCurrentText("C2 Hercules")
    tab.on_ship_changed()
    select_first_contract(tab)
    tab.toggle_selected_loaded()
    qapp.processEvents()

    assert tab.manifest.ship_capacity_scu == 696
    assert tab.manifest.remaining_scu == 196
    assert tab.manifest.loaded_scu == 500

    tab.ship_combo.setCurrentText("Caterpillar")
    tab.on_ship_changed()
    qapp.processEvents()

    assert tab.manifest.ship_capacity_scu == 576
    assert tab.manifest.remaining_scu == 76
    tab.close()


def test_hauling_tab_over_capacity_warning(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Caterpillar")
    tab.contract_text.setPlainText(sample_contract_text(quantity=700))

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.manifest.remaining_scu == 576
    assert "Planned manifest exceeds capacity" in tab.capacity_warning_label.text()
    assert "Planned manifest exceeds ship capacity" in tab.warnings_text.toPlainText()

    select_first_contract(tab)
    tab.toggle_selected_loaded()
    qapp.processEvents()

    assert tab.manifest.remaining_scu == -124
    assert "exceeds ship capacity" in tab.capacity_warning_label.text()
    assert "exceeds ship capacity" in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_no_contracts_warning(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.contract_text.setPlainText("noise only")

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.contracts == ()
    assert "No hauling contracts parsed" in tab.status_label.text()
    assert "No contracts parsed." in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_grouped_views(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Railen")
    tab.contract_text.setPlainText(
        """
        Pick up: Checkmate
        Deliver to: Teasa Spaceport
        Commodity: Construction Materials
        Quantity: 32 SCU

        Pick up: Checkmate
        Deliver to: Lorville
        Commodity: Medical Supplies
        Quantity: 12 SCU
        """
    )

    tab.parse_contracts()
    qapp.processEvents()

    assert tab.pickup_table.rowCount() == 1
    assert tab.pickup_table.item(0, 0).text() == "Checkmate"
    assert tab.pickup_table.item(0, 1).text() == "44"
    assert tab.pickup_table.item(0, 2).text() == "44"
    assert tab.pickup_table.item(0, 3).text() == "0"
    assert tab.pickup_table.item(0, 4).text() == "2"
    assert tab.pickup_table.item(0, 5).text() == "0"
    assert tab.destination_table.rowCount() == 2
    assert tab.route_table.rowCount() == 2
    manifest_text = tab.manifest_text()
    assert "Construction Materials" in manifest_text
    assert "Medical Supplies" in manifest_text
    tab.close()


def test_hauling_tab_live_cargo_operations_update_progress_and_events(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ship_combo.setCurrentText("Railen")
    tab.contract_text.setPlainText(sample_contract_text(quantity=32))
    tab.parse_contracts()
    qapp.processEvents()

    assert tab.contracts[0].state == CONTRACT_STATE_PLANNED
    assert tab.progress_bar.value() == 0

    select_first_contract(tab)
    tab.toggle_selected_loaded()
    qapp.processEvents()

    assert tab.contracts[0].state == CONTRACT_STATE_LOADED
    assert tab.manifest.loaded_scu == 32
    assert tab.manifest.delivered_scu == 0
    assert tab.manifest.remaining_scu == 608
    assert tab.dashboard_labels["loaded_contracts"].text() == "1"
    assert tab.contracts_table.item(0, 0).text() == "Loaded"

    select_first_contract(tab)
    tab.toggle_selected_delivered()
    qapp.processEvents()

    assert tab.contracts[0].state == CONTRACT_STATE_DELIVERED
    assert tab.manifest.loaded_scu == 32
    assert tab.manifest.delivered_scu == 32
    assert tab.manifest.remaining_scu == 608
    assert tab.manifest.completion_percentage == 100
    assert tab.progress_bar.value() == 100
    assert "Everything delivered." in tab.warnings_text.toPlainText()

    select_first_contract(tab)
    tab.toggle_selected_loaded()
    qapp.processEvents()

    assert tab.contracts[0].state == CONTRACT_STATE_DELIVERED
    assert "Delivered contracts remain loaded" in tab.status_label.text()

    events = reload_module("app.event_center.storage").list_notification_events(category="Hauling")
    event_types = [event.event_type for event in events]
    assert "hauling_manifest_started" in event_types
    assert "hauling_contract_loaded" in event_types
    assert "hauling_contract_delivered" in event_types
    assert "hauling_manifest_completed" in event_types
    for event in events:
        assert "Checkmate" not in event.message
        assert "Checkmate" not in str(event.metadata)
    tab.close()


def test_hauling_tab_ocr_capture_updates_manifest(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    save_hauling_region(tab)
    tab.ship_combo.setCurrentText("Railen")
    tab.ocr_service = FakeOCRService(sample_contract_text(quantity=48))
    tab.start_ocr_worker = run_ocr_synchronously

    tab.capture_contracts_ocr()
    qapp.processEvents()

    assert len(tab.contracts) == 1
    assert tab.contract_text.toPlainText().strip()
    assert tab.manifest.selected_ship == "Railen"
    assert tab.manifest.ship_capacity_scu == 640
    assert tab.manifest.total_scu == 48
    assert tab.manifest.remaining_scu == 640
    assert "OCR captured and parsed 1 contract candidate" in tab.status_label.text()
    assert not tab.ocr_capture_running
    assert tab.capture_ocr_button.isEnabled()

    profile, region, parser = tab.ocr_service.calls[0]
    assert profile.key == "hauling_contracts"
    assert region.profile == "hauling_contracts"
    assert region.to_tuple() == (10, 20, 300, 120)
    assert parser.name == "hauling_contracts"

    events = reload_module("app.event_center.storage").list_notification_events(category="Hauling")
    event_types = {event.event_type for event in events}
    assert "hauling_manifest_started" in event_types
    assert "hauling_ocr_scan" in event_types
    for event in events:
        assert "Checkmate" not in event.message
        assert "Checkmate" not in str(event.metadata)
    tab.close()


def test_hauling_tab_ocr_empty_text_is_inline_warning(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    save_hauling_region(tab)
    tab.ocr_service = FakeOCRService("")
    tab.start_ocr_worker = run_ocr_synchronously

    tab.capture_contracts_ocr()
    qapp.processEvents()

    assert tab.contracts == ()
    assert "no text was detected" in tab.status_label.text()
    assert "No contracts parsed." in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_ocr_malformed_text_does_not_crash(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    save_hauling_region(tab)
    tab.ocr_service = FakeOCRService("random screen noise")
    tab.start_ocr_worker = run_ocr_synchronously

    tab.capture_contracts_ocr()
    qapp.processEvents()

    assert tab.contracts == ()
    assert "no hauling contracts were parsed" in tab.status_label.text()
    assert "No hauling contract fields detected." in tab.warnings_text.toPlainText()
    tab.close()


def test_hauling_tab_ocr_missing_region_is_inline_status(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ocr_service = FakeOCRService(sample_contract_text())
    tab.start_ocr_worker = run_ocr_synchronously

    tab.capture_contracts_ocr()
    qapp.processEvents()

    assert tab.ocr_service.calls == []
    assert "No OCR capture region saved" in tab.status_label.text()
    tab.close()


def test_hauling_tab_ocr_repeated_capture_is_ignored(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    save_hauling_region(tab)
    tab.ocr_service = FakeOCRService(sample_contract_text())
    tab.start_ocr_worker = run_ocr_synchronously
    tab.ocr_capture_running = True

    tab.capture_contracts_ocr()
    qapp.processEvents()

    assert tab.ocr_service.calls == []
    assert "already running" in tab.status_label.text()
    tab.close()


def test_hauling_tab_ocr_stale_result_is_ignored(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    tab.ocr_capture_request_id = 2
    ocr_result = OCRResult(text=sample_contract_text())
    parser = reload_module("app.ocr.hauling").HaulingContractsOCRParser()
    result = OCRPipelineResult(
        status="ok",
        ocr_result=ocr_result,
        parsed_result=parser.parse(ocr_result),
    )

    tab.on_ocr_capture_result(1, result)
    qapp.processEvents()

    assert tab.contract_text.toPlainText() == ""
    assert tab.contracts == ()
    assert tab.contracts_table.rowCount() == 0
    tab.close()


def test_hauling_tab_ocr_falls_back_to_reward_scanner_region(monkeypatch, tmp_path, qapp):
    tab = build_tab(monkeypatch, tmp_path)
    profiles = reload_module("app.ocr.profiles")
    regions = reload_module("app.ocr.regions")
    tab.ocr_profile_manager.save_region(
        regions.OCRRegion.from_tuple(
            (1, 2, 30, 40),
            profile=profiles.REWARD_SCANNER_PROFILE_KEY,
            name="Reward Scanner",
        )
    )

    region = tab.ocr_region()

    assert region.profile == profiles.HAULING_CONTRACTS_PROFILE_KEY
    assert region.to_tuple() == (1, 2, 30, 40)
    tab.close()
