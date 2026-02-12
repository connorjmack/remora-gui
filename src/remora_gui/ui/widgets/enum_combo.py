"""Enum combo box wrapper that emits string values."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QWidget


class EnumComboBox(QComboBox):
    """QComboBox that emits the selected string on change."""

    enum_value_changed = pyqtSignal(str)

    def __init__(self, options: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.addItems(options)
        self.currentTextChanged.connect(self.enum_value_changed.emit)

    def value(self) -> str:
        """Return the currently selected string."""
        return self.currentText()

    def set_value(self, text: str) -> None:
        """Select the given option by text."""
        idx = self.findText(text)
        if idx >= 0:
            self.setCurrentIndex(idx)
