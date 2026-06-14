from .shared import *


class MiningRockBreakerMixin:
    def build_rock_breaker_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        input_card = self.create_filter_card("ROCK PROFILE")
        input_layout = input_card.layout()
        row = QHBoxLayout()
        self.rock_mass_input = QLineEdit()
        self.rock_mass_input.setPlaceholderText("Mass...")
        self.rock_resistance_input = QLineEdit()
        self.rock_resistance_input.setPlaceholderText("Resistance %...")
        self.rock_resistance_input.setToolTip(
            "Resistance % - enter 10 for 10% or 0.10; both are accepted."
        )
        self.rock_instability_input = QLineEdit()
        self.rock_instability_input.setPlaceholderText("Instability...")
        self.rock_laser_filter = self.create_combo(["Any laser", "Ship mining", "Vehicle mining", "Hand mining"])
        self.rock_calculate_button = QPushButton("Analyze")
        row.addWidget(self.rock_mass_input)
        row.addWidget(self.rock_resistance_input)
        row.addWidget(self.rock_instability_input)
        row.addWidget(self.rock_laser_filter)
        row.addWidget(self.rock_calculate_button)
        input_layout.addLayout(row)
        layout.addWidget(input_card)

        self.rock_table = self.create_table([
            "Setup",
            "Laser",
            "Modules",
            "Power Window",
            "Risk",
            "Notes",
        ])
        self.rock_table.setSortingEnabled(False)
        configure_readable_table_columns(self.rock_table, min_width=110, max_width=360, stretch_last=True)
        layout.addWidget(self.rock_table, 1)
        self.rock_empty_label = self.create_empty_state("No rock-breaking setups match the current filters.")
        layout.addWidget(self.rock_empty_label)
        widget.setLayout(layout)
        return widget


    def populate_rock_breaker_results(self):
        lasers = [
            laser
            for laser in self.mining_data.rock_lasers
            if self.rock_laser_matches_filter(laser)
        ]
        mass = self.parse_float(self.rock_mass_input.text())
        resistance_text = self.rock_resistance_input.text().strip()
        resistance = self.normalize_rock_resistance(self.parse_float(resistance_text))
        instability = self.parse_float(self.rock_instability_input.text())
        has_power_stats = mass > 0 and bool(resistance_text)

        if not has_power_stats:
            rows = [
                [
                    "Baseline",
                    f"{laser.name} S{laser.size}",
                    f"{laser.module_slots} slots",
                    f"{self.format_number(laser.min_power)}-{self.format_number(laser.max_power)}",
                    "Enter rock stats",
                    (
                        f"Price {self.format_auec_amount(laser.price or 0)} | "
                        f"Res x{laser.resistance_factor:g} | Instab x{laser.instability_factor:g} | "
                        f"Window x{laser.optimal_charge_window:g}"
                    ),
                ]
                for laser in sorted(lasers, key=lambda item: (item.size, item.name.lower()))
            ]
            self.set_table_rows(self.rock_table, rows)
            self.color_rock_risk_cells()
            self.rock_empty_label.setVisible(not rows)
            return

        module_candidates = self.rock_module_candidates()
        gadgets = [None, *self.mining_data.rock_gadgets]
        setups = []
        for laser in lasers:
            for modules in self.rock_module_combinations(module_candidates, laser.module_slots):
                for gadget in gadgets:
                    setups.append(self.evaluate_rock_setup(laser, modules, gadget, mass, resistance, instability))

        setups.sort(key=lambda item: item["score"])
        rows = []
        for rank, setup in enumerate(setups[:120], start=1):
            rows.append([
                f"#{rank} {setup['setup']}",
                setup["laser"],
                setup["modules"],
                setup["power_window"],
                setup["risk"],
                setup["notes"],
            ])

        self.set_table_rows(self.rock_table, rows)
        self.color_rock_risk_cells()
        self.rock_empty_label.setVisible(not rows)


    def rock_laser_matches_filter(self, laser):
        selected = self.rock_laser_filter.currentText()
        if selected == "Ship mining":
            return laser.size >= 1
        if selected in {"Vehicle mining", "Hand mining"}:
            return laser.size == 0
        return True


    def normalize_rock_resistance(self, value):
        resistance = max(float(value or 0), 0.0)
        if resistance >= 1:
            resistance /= 100
        return resistance


    def format_rock_resistance_percent(self, value):
        text = f"{value * 100:.2f}".rstrip("0").rstrip(".")
        return f"{text}%"


    def rock_module_candidates(self):
        return [
            module
            for module in self.mining_data.rock_modules
            if any(
                abs(value - 1) > 0.001
                for value in (
                    module.mining_laser_power,
                    module.resistance_factor,
                    module.instability_factor,
                    module.optimal_charge_rate,
                    module.optimal_charge_window,
                )
            )
        ]


    def rock_module_combinations(self, modules, slots):
        if slots <= 0:
            return [()]

        combos = [()]
        for size in range(1, min(slots, 3) + 1):
            combos.extend(combinations(modules, size))
        return combos


    def evaluate_rock_setup(self, laser, modules, gadget, mass, resistance, instability):
        power_factor = self.multiply_factors([module.mining_laser_power for module in modules])
        resistance_factor = laser.resistance_factor * self.multiply_factors(
            [module.resistance_factor for module in modules]
        )
        instability_factor = laser.instability_factor * self.multiply_factors(
            [module.instability_factor for module in modules]
        )
        charge_rate = laser.optimal_charge_rate * self.multiply_factors(
            [module.optimal_charge_rate for module in modules]
        )
        charge_window = laser.optimal_charge_window * self.multiply_factors(
            [module.optimal_charge_window for module in modules]
        )

        if gadget:
            resistance_factor *= gadget.resistance_factor
            instability_factor *= gadget.instability_factor
            charge_window *= gadget.optimal_charge_window
            charge_rate *= gadget.optimal_charge_rate

        min_power = laser.min_power * power_factor
        max_power = laser.max_power * power_factor
        required_power = mass * resistance * resistance_factor
        rock_instability = instability if instability > 0 else 1
        effective_instability = rock_instability * instability_factor
        risk_score = effective_instability / max(charge_window, 0.1)

        if required_power > max_power:
            risk = "Too weak"
            score = 100000 + ((required_power / max(max_power, 1)) * 1000) + risk_score
            setup = "Needs more power"
        elif required_power < min_power:
            risk = "Overpowered"
            score = 50000 + ((min_power / max(required_power, 1)) * 250) + risk_score
            setup = "Throttle carefully"
        else:
            if risk_score >= 1.35 or effective_instability >= 1.5 or charge_window < 0.7:
                risk = "High"
            elif risk_score >= 0.85 or effective_instability >= 1.1 or charge_window < 1:
                risk = "Medium"
            else:
                risk = "Low"

            score = (
                risk_score * 100
                - min(max_power - required_power, max_power) / max(max_power, 1) * 20
                + len(modules) * 4
                + (6 if gadget else 0)
            )
            setup = "Recommended" if risk == "Low" else "Workable"

        module_text = ", ".join(module.name for module in modules) or "None"
        if gadget:
            module_text = f"{module_text} + {gadget.name} gadget"

        notes = (
            f"S{laser.size} | Slots {laser.module_slots} | "
            f"Input Res {self.format_rock_resistance_percent(resistance)} | "
            f"Res x{resistance_factor:.2f} | Instab x{effective_instability:.2f} | "
            f"Window x{charge_window:.2f} | Rate x{charge_rate:.2f}"
        )
        if required_power > max_power:
            notes += f" | Needs {required_power / max(max_power, 1):.1f}x max power"

        return {
            "score": score,
            "setup": setup,
            "laser": f"{laser.name} S{laser.size}",
            "modules": module_text,
            "power_window": (
                f"Need {self.format_number(required_power)} / "
                f"{self.format_number(min_power)}-{self.format_number(max_power)}"
            ),
            "risk": risk,
            "notes": notes,
        }


    def multiply_factors(self, values):
        result = 1.0
        for value in values:
            result *= value
        return result


    def color_rock_risk_cells(self):
        colors = {
            "Low": QColor("#5cffbd"),
            "Medium": QColor("#ffd166"),
            "High": QColor("#ff8f66"),
            "Too weak": QColor("#ff5c5c"),
            "Overpowered": QColor("#ffb86b"),
        }
        for row in range(self.rock_table.rowCount()):
            item = self.rock_table.item(row, 4)
            if item and item.text() in colors:
                item.setForeground(colors[item.text()])

