from dataclasses import replace
from datetime import datetime, timedelta

import requests
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.cstone_client import (
    CSTONE_HOME_URL,
    CStoneError,
    CStoneItem,
    CStoneLocation,
    cstone_category_labels,
    cstone_category_url,
    fetch_cstone_location_inventory,
    fetch_cstone_location_names,
    fetch_cstone_item_locations,
    fetch_cstone_items,
)
from app.scfocus_client import (
    SCFOCUS_SHIPS_URL,
    SPECIAL_ACQUISITION_CATEGORY,
    WIKELO_CATEGORY,
    fetch_scfocus_ship_items,
)
from app.ship_metadata import ship_metadata_for

from ..table_utils import configure_readable_table_columns
from ..workers import BackgroundTaskMixin


SORT_ROLE = Qt.UserRole + 1
SHIP_SALE_CATEGORY = "Ships for Sale"
SHIP_RENT_CATEGORY = "Ships for Rent"
SHIP_SALE_SOURCE_CATEGORIES = {SHIP_SALE_CATEGORY, WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY}
SHIP_CATEGORIES = {SHIP_SALE_CATEGORY, SHIP_RENT_CATEGORY, WIKELO_CATEGORY, SPECIAL_ACQUISITION_CATEGORY}


class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if left is not None or right is not None:
            return self.sort_key(left) < self.sort_key(right)

        return super().__lt__(other)

    @staticmethod
    def sort_key(value):
        if value is None:
            return (2, "")
        if isinstance(value, (int, float)):
            return (0, float(value))

        return (1, str(value).lower())

