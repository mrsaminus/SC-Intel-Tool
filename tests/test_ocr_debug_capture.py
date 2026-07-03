import json
import os
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from conftest import isolated_database, reload_module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_ocr_debug_path_is_under_active_app_data(monkeypatch, tmp_path):
    _database, _db_path = isolated_database(monkeypatch, tmp_path)
    debug_capture = reload_module("app.ocr.debug_capture")
    paths = reload_module("app.paths")

    root = debug_capture.get_ocr_debug_root(create=True)

    assert root == paths.get_active_data_dir() / "ocr_debug"
    assert root.exists()


def test_ocr_debug_session_saves_trigger_and_full_outputs(tmp_path):
    debug_capture = reload_module("app.ocr.debug_capture")
    store = debug_capture.OCRDebugCaptureStore(root=tmp_path / "ocr_debug")
    session = store.start_session("blueprint_reward", metadata={"scanner_state": "Idle"})
    image = Image.new("RGB", (8, 4), color=(10, 20, 30))

    session.save_image("trigger.png", image)
    session.save_text("trigger_ocr.txt", "Received Blueprint:")
    session.save_image("full_region.png", image)
    session.save_text("full_ocr.txt", "Received Blueprint:\nField Recon Helmet")
    session.update_metadata({
        "trigger_match": True,
        "region": {"x": 1, "y": 2, "width": 8, "height": 4},
        "parser_warnings": ("low confidence",),
    })

    metadata = json.loads((session.path / "metadata.json").read_text(encoding="utf-8"))
    assert (session.path / "trigger.png").exists()
    assert (session.path / "full_region.png").exists()
    assert (session.path / "trigger_ocr.txt").read_text(encoding="utf-8") == "Received Blueprint:"
    assert metadata["workflow"] == "blueprint_reward"
    assert metadata["scanner_state"] == "Idle"
    assert metadata["trigger_match"] is True
    assert metadata["parser_warnings"] == ["low confidence"]


def test_ocr_debug_retention_keeps_latest_sessions(tmp_path):
    debug_capture = reload_module("app.ocr.debug_capture")
    store = debug_capture.OCRDebugCaptureStore(root=tmp_path / "ocr_debug", retention=2)

    first = store.start_session("hauling_contracts")
    second = store.start_session("hauling_contracts")
    third = store.start_session("hauling_contracts")

    remaining = sorted((tmp_path / "ocr_debug" / "hauling_contracts").iterdir())
    assert len(remaining) == 2
    assert first.path not in remaining
    assert second.path in remaining
    assert third.path in remaining


def test_ocr_debug_clear_all_removes_sessions(monkeypatch, tmp_path):
    _database, _db_path = isolated_database(monkeypatch, tmp_path)
    debug_capture = reload_module("app.ocr.debug_capture")

    session = debug_capture.start_ocr_debug_session("blueprint_reward")
    assert session is not None
    assert debug_capture.count_debug_capture_sessions() == 1

    removed = debug_capture.clear_ocr_debug_captures()

    assert removed == 1
    assert debug_capture.count_debug_capture_sessions() == 0
    assert not debug_capture.get_ocr_debug_root().exists()


def test_ocr_debug_enabled_setting_defaults_on_for_alpha_and_can_disable(monkeypatch, tmp_path):
    _database, _db_path = isolated_database(monkeypatch, tmp_path)
    debug_capture = reload_module("app.ocr.debug_capture")

    assert debug_capture.is_ocr_debug_enabled()

    debug_capture.set_ocr_debug_enabled(False)

    assert not debug_capture.is_ocr_debug_enabled()
    assert debug_capture.start_ocr_debug_session("blueprint_reward") is None


def test_gitignore_protects_ocr_debug_folder():
    gitignore = (Path.cwd() / ".gitignore").read_text(encoding="utf-8")

    assert "ocr_debug/" in gitignore


def test_settings_displays_ocr_debug_controls(monkeypatch, tmp_path, qapp):
    _database, _db_path = isolated_database(monkeypatch, tmp_path)
    settings_module = reload_module("app.gui.settings_tab")

    settings = settings_module.SettingsTab()
    settings.show()
    qapp.processEvents()

    assert settings.ocr_debug_enabled_checkbox.isChecked()
    assert settings.open_ocr_debug_folder_button.text() == "Open OCR Debug Folder"
    assert settings.clear_ocr_debug_button.text() == "Clear OCR Debug Captures"
    assert "ocr_debug" in settings.ocr_debug_path_label.toolTip()
    assert "Retention keeps the latest 50 sessions" in settings.ocr_debug_status_label.text()
    settings.close()
