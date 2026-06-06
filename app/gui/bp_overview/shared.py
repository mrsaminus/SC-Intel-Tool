from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

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
        lines.append("- No material data available.")

    quality_lines = grouped_quality_effect_lines(blueprint, limit=10)
    if quality_lines:
        lines.append("Quality scaling:")
        lines.extend(quality_lines)

    if blueprint.missions:
        lines.append("Mission / drop context:")
        for mission in blueprint.missions[:8]:
            chance = f" ({mission.drop_chance})" if mission.drop_chance else ""
            lines.append(f"- {mission.name}{chance}")
        if len(blueprint.missions) > 8:
            lines.append(f"- ...and {len(blueprint.missions) - 8} more")
    else:
        lines.append("Mission / drop context: Not available.")

    return "\n".join(lines)


def grouped_quality_effect_lines(blueprint, limit=None):
    grouped = {}
    for ingredient in blueprint.ingredients:
        for effect in ingredient.quality_effects:
            stat, detail = split_quality_effect(effect)
            grouped.setdefault(stat, []).append((ingredient.slot, ingredient.name, detail))

    lines = []
    count = 0
    for stat, entries in grouped.items():
        lines.append(f"- {stat}")
        for slot, name, detail in entries:
            count += 1
            if limit is not None and count > limit:
                remaining = sum(len(items) for items in grouped.values()) - limit
                lines.append(f"  - ...and {remaining} more")
                return lines
            label = f"{slot} / {name}" if slot and slot != "Material" else name
            lines.append(f"  - {label}: {detail}")
    return lines


def split_quality_effect(effect):
    if ":" not in effect:
        return effect, "scales with material quality"
    stat, detail = effect.split(":", 1)
    return stat.strip() or "Quality", detail.strip() or "scales with material quality"
