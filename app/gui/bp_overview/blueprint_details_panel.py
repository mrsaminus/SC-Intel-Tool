from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.blueprints_storage import set_blueprint_owned
from app.event_center.service import record_event

from .shared import blueprint_summary, create_card, format_duration, format_number, source_attribution_text


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
        self.subtitle_label = QLabel("Select a blueprint to inspect recipe and source details.")
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

        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addWidget(self.owned_checkbox)
        card_layout.addWidget(self.details_text, 1)
        card_layout.addWidget(self.copy_button)
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

        if not blueprint:
            self.title_label.setText("No blueprint selected")
            self.subtitle_label.setText("Select a blueprint to inspect recipe and source details.")
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

        lines = [
            f"Blueprint: {self.blueprint.blueprint_name}",
            f"Crafted item: {self.blueprint.crafted_item}",
            f"Category/type: {self.blueprint.category or 'N/A'}",
            f"Craft time: {format_duration(self.blueprint.craft_time_seconds)}",
            f"Patch/version: {self.blueprint.patch or 'N/A'}",
            f"Owned: {'Yes' if self.owned else 'No'}",
            "",
            "Recipe/material requirements:",
        ]
        if self.blueprint.ingredients:
            for ingredient in self.blueprint.ingredients:
                quality = f", min quality {format_number(ingredient.min_quality)}" if ingredient.min_quality else ""
                lines.append(
                    f"- {ingredient.slot}: {ingredient.name} x{format_number(ingredient.quantity)} "
                    f"{ingredient.unit}{quality}".strip()
                )
        else:
            lines.append("- No material data available from current source.")

        quality_lines = []
        for ingredient in self.blueprint.ingredients:
            for effect in ingredient.quality_effects:
                quality_lines.append(f"- {ingredient.slot} / {ingredient.name}: {effect}")
        lines.extend(["", "Quality/effect info:"])
        if quality_lines:
            lines.extend(quality_lines[:24])
            if len(quality_lines) > 24:
                lines.append(f"- ...and {len(quality_lines) - 24} more")
        else:
            lines.append("- No quality-effect data available from current source.")

        lines.extend(["", "Mission/source context:"])
        if self.blueprint.missions:
            for mission in self.blueprint.missions[:24]:
                chance = f" | drop chance: {mission.drop_chance}" if mission.drop_chance else ""
                lines.append(f"- {mission.name}{chance}")
            if len(self.blueprint.missions) > 24:
                lines.append(f"- ...and {len(self.blueprint.missions) - 24} more")
        else:
            lines.append("- Mission/source data not available from current source.")

        lines.extend(["", source_attribution_text()])
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
