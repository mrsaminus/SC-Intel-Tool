from dataclasses import dataclass

import pytest
from PySide6.QtWidgets import QApplication

from app.ocr.parser import ParsedOCRResult
from app.ocr.results import OCRPipelineResult, OCRResult
from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@dataclass(frozen=True)
class BlueprintStub:
    key: str
    blueprint_name: str
    ownable: bool = True


def build_scanner_tab(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    tab_module = reload_module("app.gui.bp_overview.reward_scanner_tab")
    tab = tab_module.RewardScannerTab()
    tab.enabled_checkbox.setChecked(True)
    tab.x_input.setText("10")
    tab.y_input.setText("20")
    tab.width_input.setText("300")
    tab.height_input.setText("120")
    return tab


def test_reward_scanner_uses_ocr_service_pipeline(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.set_blueprints([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    calls = []

    class FakeOCRService:
        def scan_profile_region(self, profile, region, parser=None):
            calls.append((profile, region, parser))
            ocr_result = OCRResult(text="Reward unlocked: Field Recon Helmet")
            return OCRPipelineResult(
                status="ok",
                ocr_result=ocr_result,
                parsed_result=parser.parse(ocr_result),
            )

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        except Exception as exc:
            if on_error:
                on_error(exc)
            else:
                raise
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert calls
    assert calls[0][0].key == "reward_scanner"
    assert calls[0][1].profile == "reward_scanner"
    assert calls[0][1].to_tuple() == (10, 20, 300, 120)
    assert calls[0][2].name == "reward_scanner"
    assert tab.ocr_text.toPlainText() == "Reward unlocked: Field Recon Helmet"
    assert tab.matches_table.rowCount() == 1
    assert tab.confirm_button.isEnabled()
    assert not tab.scan_once_running
    assert tab.scan_once_button.isEnabled()
    tab.close()


def test_reward_scanner_repeated_scan_is_ignored(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.scan_once_running = True
    calls = []
    tab.start_background_task = lambda *args, **kwargs: calls.append(args)

    tab.scan_once()
    qapp.processEvents()

    assert calls == []
    assert "Scan already running" in tab.status_label.text()
    tab.close()


def test_reward_scanner_stale_result_is_ignored(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.scan_once_request_id = 2

    tab.on_scan_once_result(
        1,
        {
            "status": "ok",
            "text": "Reward unlocked: Field Recon Helmet",
            "matches": [{"blueprint": BlueprintStub("field-recon-helmet", "Field Recon Helmet"), "confidence": 1.0, "match_type": "exact"}],
            "blueprint_count": 1,
        },
    )
    qapp.processEvents()

    assert tab.ocr_text.toPlainText() == ""
    assert tab.matches_table.rowCount() == 0
    tab.close()


def test_reward_scanner_pipeline_parse_error_shows_scan_failure(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.scan_once_request_id = 1
    pipeline = OCRPipelineResult(
        status="parse_error",
        ocr_result=OCRResult(text="bad text"),
        parsed_result=ParsedOCRResult(errors=("parser exploded",)),
        message="parser exploded",
        errors=("parser exploded",),
    )
    tab_module = reload_module("app.gui.bp_overview.reward_scanner_tab")

    tab.on_scan_once_result(
        1,
        tab_module.reward_scan_result_from_pipeline(pipeline, blueprint_count=1),
    )
    qapp.processEvents()

    assert "Scan failed locally: parser exploded" in tab.status_label.text()
    tab.close()
