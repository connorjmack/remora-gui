"""Parameter diff dialog — side-by-side comparison of two runs."""

from __future__ import annotations

from typing import Any

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.param_diff import DiffEntry, diff_parameters


class ParamDiffDialog(QDialog):
    """Show a side-by-side diff of two parameter sets."""

    _COLOR_ADDED = QColor("#2f855a")   # green
    _COLOR_REMOVED = QColor("#c53030")  # red
    _COLOR_CHANGED = QColor("#b7791f")  # yellow/amber

    def __init__(
        self,
        params_a: dict[str, Any],
        params_b: dict[str, Any],
        label_a: str = "Run A",
        label_b: str = "Run B",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Parameter Diff: {label_a} vs {label_b}")
        self.resize(800, 500)

        self._params_a = params_a
        self._params_b = params_b
        self._label_a = label_a
        self._label_b = label_b
        self._diffs = diff_parameters(params_a, params_b)

        self._setup_ui()
        self._populate()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        self._show_all_cb = QCheckBox("Show all parameters (not just differences)")
        self._show_all_cb.toggled.connect(self._populate)
        layout.addWidget(self._show_all_cb)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Parameter", self._label_a, self._label_b])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

    def _populate(self) -> None:
        show_all = self._show_all_cb.isChecked()
        self._table.setSortingEnabled(False)

        if show_all:
            self._populate_all()
        else:
            self._populate_diffs_only()

        self._table.setSortingEnabled(True)

    def _populate_diffs_only(self) -> None:
        self._table.setRowCount(len(self._diffs))
        for i, entry in enumerate(self._diffs):
            self._set_diff_row(i, entry)

    def _populate_all(self) -> None:
        all_keys = sorted(set(self._params_a) | set(self._params_b))
        diff_map = {d.key: d for d in self._diffs}
        self._table.setRowCount(len(all_keys))

        for i, key in enumerate(all_keys):
            if key in diff_map:
                self._set_diff_row(i, diff_map[key])
            else:
                val = self._params_a.get(key, "")
                self._table.setItem(i, 0, QTableWidgetItem(key))
                self._table.setItem(i, 1, QTableWidgetItem(_fmt(val)))
                self._table.setItem(i, 2, QTableWidgetItem(_fmt(val)))

    def _set_diff_row(self, row: int, entry: DiffEntry) -> None:
        key_item = QTableWidgetItem(entry.key)
        a_item = QTableWidgetItem(_fmt(entry.value_a) if entry.value_a is not None else "—")
        b_item = QTableWidgetItem(_fmt(entry.value_b) if entry.value_b is not None else "—")

        color = {
            "added": self._COLOR_ADDED,
            "removed": self._COLOR_REMOVED,
            "changed": self._COLOR_CHANGED,
        }[entry.kind]

        for item in (key_item, a_item, b_item):
            item.setForeground(color)

        self._table.setItem(row, 0, key_item)
        self._table.setItem(row, 1, a_item)
        self._table.setItem(row, 2, b_item)


def _fmt(value: Any) -> str:
    """Format a parameter value for display."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)
