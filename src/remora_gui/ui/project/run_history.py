"""Run history table widget with context menu and diff support."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHeaderView,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.project import Project, SimulationRun
from remora_gui.ui.dialogs.param_diff_dialog import ParamDiffDialog


class RunHistory(QWidget):
    """Table showing run history for the current project."""

    run_selected = pyqtSignal(str)  # Emits run_id
    run_deleted = pyqtSignal(str)   # Emits run_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Status", "Date", "Machine", "Duration", "Notes"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

    def set_project(self, project: Project) -> None:
        """Populate the table from project runs."""
        self._project = project
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(project.runs))
        for i, run in enumerate(project.runs):
            name_item = QTableWidgetItem(run.name)
            name_item.setData(Qt.ItemDataRole.UserRole, run.id)
            self._table.setItem(i, 0, name_item)
            self._table.setItem(i, 1, QTableWidgetItem(run.status))
            date_str = run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else ""
            self._table.setItem(i, 2, QTableWidgetItem(date_str))
            self._table.setItem(
                i, 3, QTableWidgetItem(run.machine_profile_id or "Local")
            )
            self._table.setItem(i, 4, QTableWidgetItem(_format_duration(run)))
            self._table.setItem(i, 5, QTableWidgetItem(run.notes))
        self._table.setSortingEnabled(True)

    def _get_run_id(self, row: int) -> str | None:
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _get_run(self, run_id: str) -> SimulationRun | None:
        if self._project is None:
            return None
        for run in self._project.runs:
            if run.id == run_id:
                return run
        return None

    def _on_double_click(self) -> None:
        row = self._table.currentRow()
        run_id = self._get_run_id(row)
        if run_id:
            self.run_selected.emit(run_id)

    def _show_context_menu(self, pos: object) -> None:
        menu = QMenu(self)
        selected = self._table.selectionModel().selectedRows()

        if len(selected) == 1:
            row = selected[0].row()
            run_id = self._get_run_id(row)
            if run_id:
                delete_action = QAction("Delete Run", self)
                delete_action.triggered.connect(lambda: self._delete_run(run_id))
                menu.addAction(delete_action)

        if len(selected) == 2:
            row_a = selected[0].row()
            row_b = selected[1].row()
            id_a = self._get_run_id(row_a)
            id_b = self._get_run_id(row_b)
            if id_a and id_b:
                diff_action = QAction("Compare Parameters...", self)
                diff_action.triggered.connect(lambda: self._diff_runs(id_a, id_b))
                menu.addAction(diff_action)

        if not menu.isEmpty():
            menu.exec(self._table.viewport().mapToGlobal(pos))  # type: ignore[arg-type]

    def _delete_run(self, run_id: str) -> None:
        reply = QMessageBox.question(
            self, "Delete Run", "Are you sure you want to delete this run?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.run_deleted.emit(run_id)

    def _diff_runs(self, id_a: str, id_b: str) -> None:
        run_a = self._get_run(id_a)
        run_b = self._get_run(id_b)
        if run_a is None or run_b is None:
            return
        dlg = ParamDiffDialog(
            run_a.input_parameters,
            run_b.input_parameters,
            label_a=run_a.name,
            label_b=run_b.name,
            parent=self,
        )
        dlg.exec()


def _format_duration(run: SimulationRun) -> str:
    """Format the run duration as a human-readable string."""
    if run.started_at is None or run.completed_at is None:
        return ""
    delta = run.completed_at - run.started_at
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"
