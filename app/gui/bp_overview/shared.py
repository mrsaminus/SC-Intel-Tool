from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.blueprints_client import SC_CRAFT_TOOLS_BASE_URL

from ..table_utils import configure_readable_table_columns


SORT_ROLE = Qt.UserRole + 1
ROW_ROLE = Qt.UserRole + 2


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


def create_card(title):
    card = QFrame()
    card.setObjectName("sectionCard")
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    title_label = QLabel(title)
    title_label.setObjectName("sectionTitle")
    layout.addWidget(title_label)
    card.setLayout(layout)
    return card


def create_header(title, subtitle):
    header = QFrame()
    header.setObjectName("playerCard")
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(4)
    title_label = QLabel(title)
    title_label.setObjectName("moduleHeading")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("moduleSubtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    header.setLayout(layout)
    return header


def create_table(headers, stretch_last=True):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(True)
    configure_readable_table_columns(table, min_width=110, max_width=360, stretch_last=stretch_last)
    return table


def table_item(text, sort_value=None):
    item = SortableTableWidgetItem(str(text or ""))
    item.setData(SORT_ROLE, sort_value if sort_value is not None else str(text or ""))
    return item


def format_number(value):
    if value is None:
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.4f}".rstrip("0").rstrip(".")


def format_duration(seconds):
    if seconds is None:
        return "N/A"
    minutes = int(seconds) // 60
    if minutes <= 0:
        return f"{seconds}s"
    return f"{minutes}m"


def blueprint_summary(blueprint, owned=False):
    lines = [
        f"Blueprint: {blueprint.blueprint_name}",
        f"Crafts: {blueprint.crafted_item}",
        f"Category: {blueprint.category or 'N/A'}",
        f"Owned: {'Yes' if owned else 'No'}",
        "Materials:",
    ]
    if blueprint.ingredients:
        for ingredient in blueprint.ingredients:
            lines.append(
                f"- {ingredient.name} x{format_number(ingredient.quantity)} {ingredient.unit}".strip()
            )
    else:
        lines.append("- No material data available from current source.")

    if blueprint.missions:
        lines.append("Sources:")
        for mission in blueprint.missions[:8]:
            chance = f" ({mission.drop_chance})" if mission.drop_chance else ""
            lines.append(f"- {mission.name}{chance}")
        if len(blueprint.missions) > 8:
            lines.append(f"- ...and {len(blueprint.missions) - 8} more")
    else:
        lines.append("Source: Mission/source data not available from current source.")

    lines.append(f"Data source: {blueprint.source}")
    return "\n".join(lines)


def source_attribution_text():
    return (
        f"Primary source: SC Craft Tools ({SC_CRAFT_TOOLS_BASE_URL}). "
        "SCMDB is documented as a secondary source-context reference; it is not loaded by this alpha tab."
    )
