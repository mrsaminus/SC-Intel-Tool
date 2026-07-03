from datetime import datetime
from itertools import combinations

import requests
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.mining_data import load_mining_data
from app.uex_client import UEXError, fetch_commodity_sell_prices

from ..constants import (
    GEM_SELLING_MATERIALS,
    REFINERY_METHODS,
    REFINERY_METHOD_YIELD_FALLBACKS,
    REFINERY_STATIONS,
    SALVAGE_REFINERY_DETAILS,
    SALVAGE_REFINERY_METHOD_YIELD_FALLBACKS,
    SALVAGE_REFINERY_MATERIALS,
    SHIP_ORE_MATERIALS,
    SHIP_REFINERY_MATERIALS,
)
from ..table_utils import configure_readable_table_columns
from ..responsive import install_scroll_area, stabilize_table
from ..workers import BackgroundTaskMixin
