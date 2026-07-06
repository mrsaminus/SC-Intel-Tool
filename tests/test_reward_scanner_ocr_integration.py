from dataclasses import dataclass

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication
from PIL import Image, ImageDraw

from app.ocr.blueprint_reward_workflow import BLUEPRINT_SCAN_INTERVAL_MS, STATE_WAITING_FOR_WINDOW_CLOSE
from app.ocr.parser import ParsedOCRResult
from app.ocr.results import OCRPipelineResult, OCRResult
from conftest import isolated_database, reload_module


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
    QThreadPool.globalInstance().waitForDone(1000)
    app.processEvents()


@dataclass(frozen=True)
class BlueprintStub:
    key: str
    blueprint_name: str
    ownable: bool = True


def toast_image():
    image = Image.new("RGB", (300, 120), color=(8, 9, 11))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((35, 40, 265, 78), radius=12, fill=(126, 126, 126))
    draw.ellipse((48, 50, 66, 68), fill=(205, 205, 205))
    draw.rectangle((82, 52, 245, 58), fill=(215, 215, 215))
    draw.rectangle((82, 64, 210, 70), fill=(188, 188, 188))
    return image


def plain_image():
    return Image.new("RGB", (300, 120), color=(8, 9, 11))


class FakeScreenshotService:
    def __init__(self, calls, image):
        self.calls = calls
        self.image = image

    def capture_region(self, region, preprocess=True, settings=None):
        self.calls.append(("capture", region, preprocess))
        return self.image


def build_scanner_tab(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    tab_module = reload_module("app.gui.bp_overview.reward_scanner_tab")
    tab = tab_module.RewardScannerTab()
    tab.x_input.setText("10")
    tab.y_input.setText("20")
    tab.width_input.setText("300")
    tab.height_input.setText("120")
    tab.enabled_checkbox.blockSignals(True)
    tab.enabled_checkbox.setChecked(True)
    tab.enabled_checkbox.blockSignals(False)
    return tab


def test_reward_scanner_uses_ocr_service_pipeline(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.set_blueprints([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, toast_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            ocr_result = OCRResult(text="Received Blueprint:\nReward unlocked: Field Recon Helmet")
            return OCRPipelineResult(
                status="ok",
                ocr_result=ocr_result,
                captured_image=image,
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

    assert len(calls) == 2
    assert calls[0][0] == "capture"
    assert calls[0][1].profile == "reward_scanner"
    assert calls[0][1].to_tuple() == (10, 20, 300, 120)
    assert calls[0][2] is False
    assert calls[1][0] == "ocr"
    assert calls[1][2] is None
    assert calls[1][3] is True
    assert tab.ocr_text.toPlainText() == "Received Blueprint:\nReward unlocked: Field Recon Helmet"
    assert tab.matches_table.rowCount() == 1
    assert tab.confirm_button.isEnabled()
    assert tab.reward_workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    assert not tab.scan_once_running
    assert tab.scan_once_button.isEnabled()
    debug_sessions = list((tmp_path / "SC-Intel-Tool" / "ocr_debug" / "blueprint_reward").iterdir())
    assert len(debug_sessions) == 1
    debug_session = debug_sessions[0]
    assert (debug_session / "trigger.png").exists()
    assert (debug_session / "full_region.png").exists()
    assert (debug_session / "trigger_ocr.txt").read_text(encoding="utf-8") == (
        "Received Blueprint:\nReward unlocked: Field Recon Helmet"
    )
    assert (debug_session / "full_ocr.txt").read_text(encoding="utf-8") == (
        "Received Blueprint:\nReward unlocked: Field Recon Helmet"
    )
    tab.close()
    tab.deleteLater()


def test_reward_scanner_does_not_run_full_ocr_without_trigger(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.set_blueprints([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, plain_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            return OCRPipelineResult(status="ok", ocr_result=OCRResult(text="No reward here"))

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        except Exception as exc:
            if on_error:
                on_error(exc)
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert len(calls) == 1
    assert calls[0][0] == "capture"
    assert tab.ocr_text.toPlainText() == ""
    assert tab.matches_table.rowCount() == 0
    assert "Watching for Blueprint notification toast" in tab.status_label.text()
    debug_root = tmp_path / "SC-Intel-Tool" / "ocr_debug" / "blueprint_reward"
    assert not debug_root.exists()
    tab.close()
    tab.deleteLater()


def test_reward_scanner_waiting_state_prevents_duplicate_full_scan(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.reward_workflow.wait_for_window_close()
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, toast_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            return OCRPipelineResult(status="ok", ocr_result=OCRResult(text="Received Blueprint:"))

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert len(calls) == 1
    assert calls[0][0] == "capture"
    assert tab.reward_workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    assert "Waiting for the toast to close" in tab.status_label.text()
    tab.close()
    tab.deleteLater()


def test_reward_scanner_returns_to_idle_when_trigger_disappears(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.reward_workflow.wait_for_window_close()

    class FakeOCRService:
        screenshot_service = FakeScreenshotService([], plain_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            return OCRPipelineResult(status="ok", ocr_result=OCRResult(text=""))

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert tab.reward_workflow.state == "Idle"
    assert "Watching for Blueprint notification toast" in tab.status_label.text()
    tab.close()
    tab.deleteLater()


def test_reward_scanner_toast_with_missing_blueprint_name_saves_debug(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.set_blueprints([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, toast_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            return OCRPipelineResult(
                status="ok",
                ocr_result=OCRResult(text="Received Blueprint:"),
                captured_image=image,
            )

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert len(calls) == 2
    assert tab.matches_table.rowCount() == 0
    assert "no blueprint name was recognized" in tab.status_label.text()
    assert tab.reward_workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    debug_sessions = list((tmp_path / "SC-Intel-Tool" / "ocr_debug" / "blueprint_reward").iterdir())
    assert len(debug_sessions) == 1
    metadata = (debug_sessions[0] / "metadata.json").read_text(encoding="utf-8")
    assert '"visual_toast_detected": true' in metadata
    assert '"text_trigger_detected": true' in metadata
    assert '"scan_interval_ms": 1000' in metadata
    tab.close()
    tab.deleteLater()


def test_reward_scanner_accepts_recieved_blueprint_ocr_typo(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.set_blueprints([BlueprintStub("field-recon-helmet", "Field Recon Helmet")])
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, toast_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            return OCRPipelineResult(
                status="ok",
                ocr_result=OCRResult(text="Recieved Blueprint:\nField Recon Helmet"),
                captured_image=image,
            )

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    tab.scan_once()
    qapp.processEvents()

    assert len(calls) == 2
    assert tab.matches_table.rowCount() == 1
    assert tab.confirm_button.isEnabled()
    assert tab.reward_workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    tab.close()
    tab.deleteLater()


def test_reward_scanner_manual_checks_are_rate_limited(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    calls = []

    class FakeOCRService:
        screenshot_service = FakeScreenshotService(calls, plain_image())

        def scan_image(self, image, parser=None, settings=None, preprocess=True):
            calls.append(("ocr", image, parser, preprocess))
            return OCRPipelineResult(status="ok", ocr_result=OCRResult(text=""))

    def run_synchronously(function, on_result=None, on_error=None, on_finished=None):
        try:
            if on_result:
                on_result(function())
        finally:
            if on_finished:
                on_finished()

    tab.ocr_service = FakeOCRService()
    tab.start_background_task = run_synchronously

    assert tab.trigger_timer.interval() >= BLUEPRINT_SCAN_INTERVAL_MS
    tab.scan_once()
    tab.scan_once()
    qapp.processEvents()

    assert len(calls) == 1
    assert "rate limited" in tab.status_label.text()
    tab.close()
    tab.deleteLater()


def test_reward_scanner_repeated_scan_is_ignored(monkeypatch, tmp_path, qapp):
    tab = build_scanner_tab(monkeypatch, tmp_path)
    tab.scan_once_running = True
    calls = []
    tab.start_background_task = lambda *args, **kwargs: calls.append(args)

    tab.scan_once()
    qapp.processEvents()

    assert calls == []
    assert "already checking" in tab.status_label.text()
    tab.close()
    tab.deleteLater()


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
    tab.deleteLater()


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
    assert tab.reward_workflow.state == STATE_WAITING_FOR_WINDOW_CLOSE
    tab.close()
    tab.deleteLater()
