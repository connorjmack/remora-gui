"""Collapsible group box widget."""

from __future__ import annotations

from PyQt6.QtCore import QPropertyAnimation, pyqtSlot
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget


class CollapsibleGroupBox(QGroupBox):
    """QGroupBox that can collapse/expand its contents."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        self.toggled.connect(self._toggle_content)

        self._content = QWidget()
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content.setLayout(self._content_layout)

        layout = QVBoxLayout()
        layout.addWidget(self._content)
        super().setLayout(layout)

        self._animation = QPropertyAnimation(self._content, b"maximumHeight")
        self._animation.setDuration(200)

    def content_layout(self) -> QVBoxLayout:
        """Return the layout where child widgets should be added."""
        return self._content_layout

    @pyqtSlot(bool)
    def _toggle_content(self, checked: bool) -> None:
        if checked:
            self._content.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
            self._content.show()
        else:
            self._content.hide()
