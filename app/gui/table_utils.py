from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView


def configure_readable_table_columns(table, min_width=90, max_width=280, stretch_last=False):
    """Size table columns for readable content, then return control to the user."""
    table.setProperty("readable_min_width", min_width)
    table.setProperty("readable_max_width", max_width)
    table.setProperty("readable_stretch_last", stretch_last)
    table.setWordWrap(False)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(min_width)

    for column in range(table.columnCount()):
        header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

    table.resizeColumnsToContents()

    for column in range(table.columnCount()):
        width = max(table.columnWidth(column), header.sectionSizeHint(column)) + 16
        width = max(min_width, min(max_width, width))
        table.setColumnWidth(column, width)
        header.setSectionResizeMode(column, QHeaderView.Interactive)

    header.setStretchLastSection(stretch_last)
