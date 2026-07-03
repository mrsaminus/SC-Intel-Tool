from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QSplitter, QWidget


DEFAULT_STACK_BREAKPOINT = 1040
DEFAULT_CARD_MIN_HEIGHT = 120
DEFAULT_TABLE_MIN_HEIGHT = 180


class ResponsiveStack(QWidget):
    """Switch child panels from horizontal to vertical before they become cramped."""

    def __init__(self, breakpoint_width=DEFAULT_STACK_BREAKPOINT, spacing=12, parent=None):
        super().__init__(parent)
        self.breakpoint_width = breakpoint_width
        self._direction = QBoxLayout.LeftToRight
        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
        self.setLayout(self._layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def addWidget(self, widget, stretch=0):
        self._layout.addWidget(widget, stretch)

    def direction(self):
        return self._direction

    def available_width(self):
        width = self.width()
        parent = self.parentWidget()
        while parent is not None:
            parent_width = parent.width()
            if parent_width > 0:
                width = min(width, parent_width)
            parent = parent.parentWidget()
        return width

    def resizeEvent(self, event):
        super().resizeEvent(event)
        desired = QBoxLayout.TopToBottom if self.available_width() < self.breakpoint_width else QBoxLayout.LeftToRight
        if desired != self._direction:
            self._direction = desired
            self._layout.setDirection(desired)


class ResponsiveSplitter(QSplitter):
    """Use side-by-side panels on wide screens and vertical panels on narrow screens."""

    def __init__(self, orientation=Qt.Horizontal, breakpoint_width=DEFAULT_STACK_BREAKPOINT, parent=None):
        super().__init__(orientation, parent)
        self.breakpoint_width = breakpoint_width
        self._wide_orientation = orientation
        self.setChildrenCollapsible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        desired = Qt.Vertical if self.width() < self.breakpoint_width else self._wide_orientation
        if self.orientation() != desired:
            self.setOrientation(desired)


def make_scroll_area(content, horizontal_policy=Qt.ScrollBarAsNeeded):
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(horizontal_policy)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    scroll_area.setWidget(content)
    return scroll_area


def install_scroll_area(parent, content, horizontal_policy=Qt.ScrollBarAsNeeded):
    scroll_area = make_scroll_area(content, horizontal_policy=horizontal_policy)
    outer_layout = QHBoxLayout()
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.addWidget(scroll_area)
    parent.setLayout(outer_layout)
    return scroll_area


def stabilize_card(card, minimum_height=DEFAULT_CARD_MIN_HEIGHT):
    card.setMinimumHeight(minimum_height)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    return card


def stabilize_table(table, minimum_height=DEFAULT_TABLE_MIN_HEIGHT):
    table.setMinimumHeight(minimum_height)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    return table
