from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class TradingTab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("playerCard")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(4)
        title = QLabel("Trading")
        title.setObjectName("moduleHeading")
        subtitle = QLabel("Market routes, commodity prices and hauling tools will live here later.")
        subtitle.setObjectName("moduleSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header.setLayout(header_layout)
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        grid.addWidget(self.create_trading_card(
            "MARKET WATCH",
            "Track commodity prices, demand and supply.",
        ), 0, 0)
        grid.addWidget(self.create_trading_card(
            "ROUTE PLANNER",
            "Compare buy/sell locations and cargo margins.",
        ), 0, 1)
        grid.addWidget(self.create_trading_card(
            "CARGO NOTES",
            "Keep local notes for hauling runs and risky terminals.",
        ), 1, 0)
        grid.addWidget(self.create_trading_card(
            "MINING LINK",
            "Use refined ore value as input for later profit planning.",
        ), 1, 1)
        grid.setRowStretch(2, 1)
        layout.addLayout(grid, 1)

        self.setLayout(layout)

    def create_trading_card(self, title, summary):
        card = QFrame()
        card.setObjectName("sectionCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        summary_label = QLabel(summary)
        summary_label.setObjectName("valueText")
        summary_label.setWordWrap(True)
        status = QLabel("Planned")
        status.setObjectName("moduleSubtitle")
        layout.addWidget(title_label)
        layout.addWidget(summary_label)
        layout.addWidget(status)
        layout.addStretch(1)
        card.setLayout(layout)
        return card
