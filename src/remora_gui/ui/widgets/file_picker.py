"""File picker widget — QLineEdit + browse button."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilePickerWidget(QWidget):
    """Line edit with a Browse button that opens a file dialog."""

    value_changed = pyqtSignal(str)

    def __init__(self, *, directory: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._directory = directory

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._line_edit = QLineEdit()
        self._line_edit.textChanged.connect(self.value_changed.emit)
        layout.addWidget(self._line_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        layout.addWidget(browse_btn)

    def value(self) -> str:
        """Return the current path text."""
        return self._line_edit.text()

    def set_value(self, path: str) -> None:
        """Set the path text."""
        self._line_edit.setText(path)

    def _browse(self) -> None:
        if self._directory:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            self._line_edit.setText(path)
