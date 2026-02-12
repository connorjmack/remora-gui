"""Project browser dock widget — tree view of projects and runs."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from remora_gui.core.project import Project


class ProjectBrowser(QDockWidget):
    """Sidebar showing project structure and run history."""

    run_selected = pyqtSignal(str)  # Emits run_id.

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Project", parent)
        self.setMinimumWidth(200)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Name", "Status"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.setWidget(self._tree)

        self._project: Project | None = None

    def set_project(self, project: Project) -> None:
        """Populate the tree from a Project."""
        self._project = project
        self._tree.clear()

        root = QTreeWidgetItem(self._tree, [project.name, ""])
        root.setExpanded(True)

        for run in project.runs:
            item = QTreeWidgetItem(root, [run.name, run.status])
            item.setData(0, 256, run.id)  # Qt.ItemDataRole.UserRole

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        run_id = item.data(0, 256)
        if run_id:
            self.run_selected.emit(run_id)
