import os

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from app.ocr.parser import OCRParser, ParsedOCRResult
from app.ocr.results import OCRResult
from app.ocr.service import OCRService
from conftest import isolated_database, reload_module

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class EchoParser(OCRParser):
    def parse(self, result):
        return ParsedOCRResult(data={"text": result.text})


def test_ocr_profile_serializes_to_settings():
    profiles = reload_module("app.ocr.profiles")

    profile = profiles.OCRProfile(
        key="test",
        name="Test Profile",
        description="Serializable profile",
        language="nor",
        preprocessing=False,
        threshold=123,
        scaling=1.5,
        invert_colors=True,
        grayscale=False,
        parser_type="echo",
    )

    loaded = profiles.OCRProfile.from_dict(profile.to_dict())
    settings = loaded.to_settings()

    assert loaded == profile
    assert settings.language == "nor"
    assert settings.preprocessing is False
    assert settings.threshold == 123
    assert settings.scale == 1.5
    assert settings.invert_colors is True
    assert settings.grayscale is False


def test_ocr_region_serialization_keeps_profile_and_monitor():
    regions = reload_module("app.ocr.regions")

    region = regions.OCRRegion.from_tuple(
        (10, 20, 300, 120),
        profile="reward_scanner",
        name="Reward Scanner",
        monitor=1,
        resolution="1920x1080",
        description="Saved reward area",
    )

    loaded = regions.OCRRegion.from_dict(region.to_dict())

    assert loaded == region
    assert loaded.is_valid()
    assert loaded.bbox() == (10, 20, 310, 140)


def test_ocr_profile_manager_defaults_and_persistence(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    profiles = reload_module("app.ocr.profiles")

    manager = profiles.OCRProfileManager()
    profile_keys = {profile.key for profile in manager.list_profiles()}
    default_profile = manager.get_profile()
    updated = profiles.OCRProfile(
        **{
            **default_profile.to_dict(),
            "language": "nor",
            "threshold": 180,
            "scaling": 2.0,
        }
    )

    assert profiles.HAULING_CONTRACTS_PROFILE_KEY in profile_keys
    assert manager.get_profile(profiles.HAULING_CONTRACTS_PROFILE_KEY).parser_type == "hauling_contracts"
    manager.save_profile(updated)
    manager.set_default_profile(updated.key)
    reloaded = profiles.OCRProfileManager()

    assert reloaded.get_default_profile_key() == profiles.REWARD_SCANNER_PROFILE_KEY
    assert reloaded.get_profile(profiles.REWARD_SCANNER_PROFILE_KEY).language == "nor"
    assert reloaded.get_profile(profiles.REWARD_SCANNER_PROFILE_KEY).threshold == 180
    assert reloaded.get_profile(profiles.REWARD_SCANNER_PROFILE_KEY).scaling == 2.0


def test_ocr_profile_manager_ignores_corrupt_settings(monkeypatch, tmp_path):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    profiles = reload_module("app.ocr.profiles")
    database.set_app_setting(profiles.OCR_PROFILES_SETTING_KEY, "{not-json")
    database.set_app_setting(profiles.OCR_DEFAULT_PROFILE_SETTING_KEY, "missing-profile")

    manager = profiles.OCRProfileManager()

    assert manager.get_default_profile_key() == profiles.REWARD_SCANNER_PROFILE_KEY
    assert manager.get_profile().name == "Reward Scanner"


def test_ocr_profile_manager_region_persistence(monkeypatch, tmp_path):
    isolated_database(monkeypatch, tmp_path)
    profiles = reload_module("app.ocr.profiles")
    regions = reload_module("app.ocr.regions")

    manager = profiles.OCRProfileManager()
    region = regions.OCRRegion.from_tuple(
        (5, 6, 70, 80),
        profile=profiles.REWARD_SCANNER_PROFILE_KEY,
        name="Reward Scanner",
    )

    manager.save_region(region)
    reloaded = profiles.OCRProfileManager().get_region(profiles.REWARD_SCANNER_PROFILE_KEY, "Reward Scanner")

    assert reloaded.to_dict() == region.to_dict()


def test_ocr_service_scan_profile_region_uses_profile_settings():
    profiles = reload_module("app.ocr.profiles")
    captured = {}

    class SettingsCapturingEngine:
        def run(self, image, settings=None):
            captured["settings"] = settings
            return OCRResult(text="configured")

    profile = profiles.OCRProfile(
        key="test",
        name="Test",
        language="nor",
        threshold=90,
        scaling=1.25,
        invert_colors=True,
        parser_type="echo",
    )
    service = OCRService(engine=SettingsCapturingEngine())

    result = service.scan_profile_region(
        profile,
        (1, 2, 3, 4),
        parser=EchoParser(),
        capture_function=lambda region: Image.new("RGB", (2, 2)),
    )

    assert result.status == "ok"
    assert result.parsed_result.data == {"text": "configured"}
    assert captured["settings"].language == "nor"
    assert captured["settings"].threshold == 90
    assert captured["settings"].scale == 1.25
    assert captured["settings"].invert_colors is True


def test_settings_ocr_section_persists_profile(monkeypatch, tmp_path, qapp):
    isolated_database(monkeypatch, tmp_path)
    settings_module = reload_module("app.gui.settings_tab")
    profiles = reload_module("app.ocr.profiles")

    settings = settings_module.SettingsTab()
    settings.ocr_language_input.setText("nor")
    settings.ocr_scale_input.setText("1.75")
    settings.ocr_threshold_input.setText("160")
    settings.ocr_preprocessing_checkbox.setChecked(True)
    settings.ocr_grayscale_checkbox.setChecked(False)
    settings.ocr_invert_checkbox.setChecked(True)

    settings.save_ocr_settings()
    qapp.processEvents()

    profile = profiles.OCRProfileManager().get_profile(profiles.REWARD_SCANNER_PROFILE_KEY)
    assert profile.language == "nor"
    assert profile.scaling == 1.75
    assert profile.threshold == 160
    assert profile.preprocessing is True
    assert profile.grayscale is False
    assert profile.invert_colors is True
    settings.close()
