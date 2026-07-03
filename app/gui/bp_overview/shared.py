from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLabel,
    QTableWidget,
    QVBoxLayout,
)

from app.blueprints_storage import normalized_material_key

from ..sortable_table_item import ROW_ROLE, SORT_ROLE, SortableTableWidgetItem
from ..responsive import stabilize_card, stabilize_table
from ..table_utils import configure_readable_table_columns


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
    return stabilize_card(card)


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
    stabilize_table(table, minimum_height=220)
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


def safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def format_duration(seconds):
    if seconds is None:
        return "N/A"
    minutes = int(seconds) // 60
    if minutes <= 0:
        return f"{seconds}s"
    return f"{minutes}m"


def aggregate_blueprint_materials(blueprint):
    materials = {}
    for ingredient in blueprint.ingredients:
        key = normalized_material_key(ingredient.name)
        if not key:
            continue
        existing = materials.setdefault(key, {
            "material_key": key,
            "material_name": ingredient.name,
            "slot": ingredient.slot or "Material",
            "required": 0.0,
            "unit": ingredient.unit or "scu",
            "min_quality": ingredient.min_quality,
        })
        if ingredient.quantity is None:
            existing["required"] = None
        elif existing["required"] is not None:
            existing["required"] += float(ingredient.quantity)
        if ingredient.min_quality:
            current_quality = existing.get("min_quality")
            existing["min_quality"] = max(current_quality or 0, ingredient.min_quality)
    return list(materials.values())


def material_status_rows(blueprint, owned_materials):
    rows = []
    for material in aggregate_blueprint_materials(blueprint):
        owned_row = owned_materials.get(material["material_key"]) or {}
        owned = safe_float(owned_row.get("quantity"), default=0)
        required = material.get("required")
        if required is None:
            missing = None
            status = "Unknown"
        else:
            missing = max(required - owned, 0)
            status = "Enough" if missing <= 0 else "Missing"
        row = dict(material)
        row.update({
            "owned": owned,
            "missing": missing,
            "status": status,
        })
        rows.append(row)
    return rows


def craftability_status(blueprint, owned_materials):
    rows = material_status_rows(blueprint, owned_materials)
    if not rows:
        return "Unknown Materials"
    if any(row["status"] == "Unknown" for row in rows):
        return "Unknown Materials"
    if all(row["status"] == "Enough" for row in rows):
        return "Craftable"
    return "Missing Materials"


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
            lines.append(format_mission_context_line(mission, style="summary"))
        if len(blueprint.missions) > 8:
            lines.append(f"- ...and {len(blueprint.missions) - 8} more")
    else:
        lines.append("Mission / drop context: Not available.")

    return "\n".join(lines)


def mission_context_parts(mission, include_drop_chance=True):
    parts = []
    if getattr(mission, "contractor", ""):
        parts.append(f"Contractor: {mission.contractor}")
    if getattr(mission, "reputation_giver", ""):
        reputation = f"Reputation: {mission.reputation_giver}"
        if getattr(mission, "reputation_rank", ""):
            reputation += f" ({mission.reputation_rank})"
        parts.append(reputation)
    elif getattr(mission, "reputation_rank", ""):
        parts.append(f"Reputation rank: {mission.reputation_rank}")
    if getattr(mission, "location", ""):
        parts.append(f"Location: {mission.location}")
    if getattr(mission, "system", ""):
        parts.append(f"System: {mission.system}")
    if include_drop_chance and getattr(mission, "drop_chance", ""):
        parts.append(f"Drop chance: {mission.drop_chance}")
    return parts


def format_mission_context_line(mission, style="details"):
    parts = mission_context_parts(mission)
    if not parts:
        return f"- {mission.name}"
    separator = " | " if style == "details" else "; "
    return f"- {mission.name} | {separator.join(parts)}"


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
