import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QLabel

from conftest import isolated_database, reload_module


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def visible_labels(widget):
    return [
        label for label in widget.findChildren(QLabel)
        if label.isVisibleTo(widget) and label.geometry().width() > 0 and label.geometry().height() > 0
    ]


def label_name(label):
    text = label.text() or label.toolTip() or label.objectName() or label.__class__.__name__
    return text.replace("\u200b", "")


def assert_wrapped_labels_have_enough_height(widget):
    for label in visible_labels(widget):
        if not label.wordWrap() or label.width() <= 0:
            continue
        needed_height = label.heightForWidth(label.width()) if label.hasHeightForWidth() else label.sizeHint().height()
        assert label.height() + 3 >= needed_height, (
            f"Label clipped: {label_name(label)!r}; "
            f"height={label.height()} needed={needed_height} width={label.width()}"
        )


def assert_no_label_overlaps(widget):
    labels_by_parent = {}
    for label in visible_labels(widget):
        labels_by_parent.setdefault(label.parentWidget(), []).append(label)

    for labels in labels_by_parent.values():
        for index, left in enumerate(labels):
            left_rect = QRect(left.geometry()).adjusted(1, 1, -1, -1)
            if left_rect.isEmpty():
                continue
            for right in labels[index + 1:]:
                right_rect = QRect(right.geometry()).adjusted(1, 1, -1, -1)
                if right_rect.isEmpty():
                    continue
                assert not left_rect.intersects(right_rect), (
                    f"Labels overlap: {label_name(left)!r} {left.geometry()} and "
                    f"{label_name(right)!r} {right.geometry()}"
                )


@pytest.mark.parametrize("theme_key", ["sc_intel_dark", "white_mode", "windows_xp", "windows_xp_black", "windows_95"])
@pytest.mark.parametrize("text_size_key", ["normal", "large", "extra_large"])
def test_settings_layout_wraps_at_reduced_width(monkeypatch, tmp_path, qapp, theme_key, text_size_key):
    database, _db_path = isolated_database(monkeypatch, tmp_path)
    database.set_app_setting("appearance.theme", theme_key)
    database.set_app_setting("appearance.text_size", text_size_key)

    theme_manager = reload_module("app.gui.themes.theme_manager")
    settings_module = reload_module("app.gui.settings_tab")

    settings = settings_module.SettingsTab()
    settings.setStyleSheet(theme_manager.stylesheet_for_theme(theme_manager.get_theme(theme_key)))
    settings.resize(560, 720)
    settings.show()
    qapp.processEvents()
    settings.layout().activate()
    qapp.processEvents()

    assert settings.settings_scroll_area.horizontalScrollBar().maximum() == 0
    assert any(label.text() == "REPOSITORY" for label in visible_labels(settings))
    assert any(label.text() == "RUNTIME" for label in visible_labels(settings))
    assert any(label.text() == "ACTIVE DATA FOLDER" for label in visible_labels(settings))
    assert any(label.text() == "ACTIVE DATABASE" for label in visible_labels(settings))
    assert any("SC Intel Tool" in label_name(label) for label in visible_labels(settings))

    assert_wrapped_labels_have_enough_height(settings)
    assert_no_label_overlaps(settings)
    settings.close()
