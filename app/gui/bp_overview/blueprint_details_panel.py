from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.blueprints_storage import get_owned_crafting_materials, set_blueprint_owned
from app.event_center.service import record_event
from app.watchlists.service import add_item_watch

from .shared import (
    blueprint_summary,
    craftability_status,
    create_card,
    format_mission_context_line,
    format_duration,
    format_number,
    grouped_quality_effect_lines,
    material_status_rows,
)


class BlueprintDetailsPanel(QWidget):
    def __init__(self, ownership_changed_callback=None):
        super().__init__()
        self.blueprint = None
        self.owned = False
        self.ownership_changed_callback = ownership_changed_callback

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        card = create_card("BLUEPRINT DETAILS")
        card_layout = card.layout()

        self.title_label = QLabel("No blueprint selected")
        self.title_label.setObjectName("orgName")
        self.title_label.setWordWrap(True)
        self.subtitle_label = QLabel("Select a blueprint to inspect recipe, quality scaling and mission details.")
        self.subtitle_label.setObjectName("moduleSubtitle")
        self.subtitle_label.setWordWrap(True)

        self.owned_checkbox = QCheckBox("Owned locally")
        self.owned_checkbox.setEnabled(False)
        self.owned_checkbox.stateChanged.connect(self.on_owned_changed)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(280)

        self.copy_button = QPushButton("Copy Recipe Summary")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_summary)
        self.watch_missing_button = QPushButton("Add Missing Materials To Watchlist")
        self.watch_missing_button.setEnabled(False)
        self.watch_missing_button.clicked.connect(self.add_missing_materials_to_watchlist)

        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addWidget(self.owned_checkbox)
        card_layout.addWidget(self.details_text, 1)
        card_layout.addWidget(self.copy_button)
        card_layout.addWidget(self.watch_missing_button)
        layout.addWidget(card, 1)
        self.setLayout(layout)

    def set_blueprint(self, blueprint, owned=False):
        self.blueprint = blueprint
        self.owned = bool(owned)
        self.owned_checkbox.blockSignals(True)
        self.owned_checkbox.setChecked(self.owned)
        self.owned_checkbox.setEnabled(blueprint is not None)
        self.owned_checkbox.blockSignals(False)
        self.copy_button.setEnabled(blueprint is not None)
        self.watch_missing_button.setEnabled(bool(blueprint and self.missing_material_rows()))

        if not blueprint:
            self.title_label.setText("No blueprint selected")
            self.subtitle_label.setText("Select a blueprint to inspect recipe, quality scaling and mission details.")
            self.details_text.setPlainText("")
            return

        self.title_label.setText(blueprint.blueprint_name)
        self.subtitle_label.setText(
            f"{blueprint.category or 'N/A'} | Craft time: {format_duration(blueprint.craft_time_seconds)} | "
            f"Patch: {blueprint.patch or 'N/A'}"
        )
        self.details_text.setPlainText(self.build_details_text())

    def build_details_text(self):
        if not self.blueprint:
            return ""

        owned_materials = get_owned_crafting_materials()
        material_rows = material_status_rows(self.blueprint, owned_materials)
        craftability = craftability_status(self.blueprint, owned_materials)

        lines = [
            f"Blueprint: {self.blueprint.blueprint_name}",
            f"Category: {self.blueprint.category or 'N/A'}",
            f"Craft time: {format_duration(self.blueprint.craft_time_seconds)}",
            f"Patch / version: {self.blueprint.patch or 'N/A'}",
            f"Owned: {'Yes' if self.owned else 'No'}",
            f"Craftability: {craftability}",
            "",
            "Recipe Materials:",
        ]
        if material_rows:
            grouped = {}
            for row in material_rows:
                grouped.setdefault(row.get("slot") or "Material", []).append(row)
            for slot, rows in grouped.items():
                lines.append(f"{slot}:")
                for row in rows:
                    required = format_number(row.get("required"))
                    owned = format_number(row.get("owned"))
                    missing = format_number(row.get("missing"))
                    quality = f" | min quality {format_number(row.get('min_quality'))}" if row.get("min_quality") else ""
                    status = row.get("status") or "Unknown"
                    unit = row.get("unit") or "scu"
                    missing_text = "Unknown" if row.get("missing") is None else f"{missing} {unit}"
                    lines.append(
                        f"- {row.get('material_name')}: required {required} {unit} | "
                        f"owned {owned} {unit} | missing {missing_text} | {status}{quality}"
                    )
        elif self.blueprint.ingredients:
            for ingredient in self.blueprint.ingredients:
                quality = f" | min quality {format_number(ingredient.min_quality)}" if ingredient.min_quality else ""
                lines.append(
                    f"- {ingredient.slot}: {ingredient.name} x{format_number(ingredient.quantity)} "
                    f"{ingredient.unit}{quality}".strip()
                )
        else:
            lines.append("- No material data available.")

        quality_lines = grouped_quality_effect_lines(self.blueprint, limit=24)
        lines.extend(["", "Quality Scaling:"])
        if quality_lines:
            lines.extend(quality_lines)
        else:
            lines.append("- No quality scaling data available.")

        lines.extend(["", "Mission / Drop Context:"])
        if self.blueprint.missions:
            for mission in self.blueprint.missions[:24]:
                lines.append(format_mission_context_line(mission))
            if len(self.blueprint.missions) > 24:
                lines.append(f"- ...and {len(self.blueprint.missions) - 24} more")
        else:
            lines.append("- Mission / drop data not available.")
        return "\n".join(lines)

    def on_owned_changed(self, *_):
        if not self.blueprint:
            return
        owned = self.owned_checkbox.isChecked()
        self.owned = owned
        set_blueprint_owned(
            self.blueprint.key,
            self.blueprint.blueprint_name,
            self.blueprint.source,
            owned,
        )
        if owned:
            record_event(
                category="Item",
                source="BP Overview",
                entity_name=self.blueprint.blueprint_name,
                event_type="blueprint_owned",
                message=f"Marked blueprint owned: {self.blueprint.blueprint_name}",
                severity="Info",
            )
        self.details_text.setPlainText(self.build_details_text())
        if self.ownership_changed_callback:
            self.ownership_changed_callback(self.blueprint, owned)

    def copy_summary(self):
        if not self.blueprint:
            return
        QApplication.clipboard().setText(blueprint_summary(self.blueprint, self.owned))

    def missing_material_rows(self):
        if not self.blueprint:
            return []
        owned_materials = get_owned_crafting_materials()
        return [
            row for row in material_status_rows(self.blueprint, owned_materials)
            if row.get("status") == "Missing"
        ]

    def add_missing_materials_to_watchlist(self):
        rows = self.missing_material_rows()
        if not rows:
            QMessageBox.information(self, "No Missing Materials", "This blueprint has no currently missing materials.")
            return
        for row in rows:
            add_item_watch(
                row.get("material_name") or row.get("material_key"),
                "Crafting Material",
                source="BP Overview",
                metadata={
                    "blueprint": self.blueprint.blueprint_name,
                    "required": row.get("required"),
                    "owned": row.get("owned"),
                    "missing": row.get("missing"),
                    "unit": row.get("unit"),
                },
            )
        QMessageBox.information(
            self,
            "Materials Added",
            f"Added {len(rows)} missing material watch{'es' if len(rows) != 1 else ''}.",
        )
