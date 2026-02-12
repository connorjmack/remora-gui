"""Variable explorer — table of variables with statistics and quick preview."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.output_reader import OutputReader


class VariableExplorer(QWidget):
    """Table showing available variables with min/max/mean and metadata."""

    # Emitted on double-click: variable name to open in slice viewer
    variable_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: OutputReader | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Variable", "Units", "Min", "Max", "Mean"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_reader(self, reader: OutputReader, time_index: int = 0) -> None:
        """Populate the table from an output reader."""
        self._reader = reader
        variables = reader.get_variables()
        self._table.setRowCount(len(variables))

        for i, var in enumerate(variables):
            self._table.setItem(i, 0, QTableWidgetItem(var))

            try:
                info = reader.get_variable_info(var)
                units = info.get("units", "")
            except (KeyError, NotImplementedError):
                units = ""
            self._table.setItem(i, 1, QTableWidgetItem(units))

            try:
                stats = reader.get_statistics(var, time_index)
                self._table.setItem(i, 2, QTableWidgetItem(f"{stats['min']:.6g}"))
                self._table.setItem(i, 3, QTableWidgetItem(f"{stats['max']:.6g}"))
                self._table.setItem(i, 4, QTableWidgetItem(f"{stats['mean']:.6g}"))
            except (KeyError, IndexError, NotImplementedError):
                self._table.setItem(i, 2, QTableWidgetItem("—"))
                self._table.setItem(i, 3, QTableWidgetItem("—"))
                self._table.setItem(i, 4, QTableWidgetItem("—"))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_double_click(self) -> None:
        row = self._table.currentRow()
        item = self._table.item(row, 0)
        if item:
            self.variable_selected.emit(item.text())
