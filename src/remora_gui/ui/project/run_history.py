"""Run history table widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from remora_gui.core.project import Project


class RunHistory(QWidget):
    """Table showing run history for the current project."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Name", "Status", "Date", "Machine", "Duration"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

    def set_project(self, project: Project) -> None:
        """Populate the table from project runs."""
        self._table.setRowCount(len(project.runs))
        for i, run in enumerate(project.runs):
            self._table.setItem(i, 0, QTableWidgetItem(run.name))
            self._table.setItem(i, 1, QTableWidgetItem(run.status))
            date_str = run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else ""
            self._table.setItem(i, 2, QTableWidgetItem(date_str))
            self._table.setItem(i, 3, QTableWidgetItem(run.machine_id or "Local"))
            self._table.setItem(i, 4, QTableWidgetItem(""))
