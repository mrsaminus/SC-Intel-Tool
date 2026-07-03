import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

from app.gui.safe_combobox import SafeComboBox


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def make_wheel_event(widget, delta=120):
    pos = QPointF(8, 8)
    return QWheelEvent(
        pos,
        QPointF(widget.mapToGlobal(QPoint(8, 8))),
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )


def test_closed_safe_combobox_ignores_wheel_without_changing_value(qapp):
    combo = SafeComboBox()
    combo.addItems(["One", "Two", "Three"])
    combo.setCurrentIndex(0)
    combo.show()
    qapp.processEvents()

    event = make_wheel_event(combo)
    QApplication.sendEvent(combo, event)

    assert combo.currentIndex() == 0
    assert not event.isAccepted()
    combo.close()
