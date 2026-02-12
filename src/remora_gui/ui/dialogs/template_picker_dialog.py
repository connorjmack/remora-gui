"""Template picker dialog — grid of template cards with preview."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.templates import list_templates, load_template


class TemplatePickerDialog(QDialog):
    """Dialog for choosing a template configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Template")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self._templates = list_templates()

        # Template list.
        self._list = QListWidget()
        for t in self._templates:
            item = QListWidgetItem(f"{t['name']}  [{t.get('category', '')}]")
            item.setData(256, t["file"])  # Qt.ItemDataRole.UserRole
            item.setToolTip(t["description"])
            self._list.addItem(item)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        # Preview label.
        self._preview = QLabel("Select a template to see its parameters.")
        self._preview.setWordWrap(True)
        self._preview.setStyleSheet("color: #a0aec0; padding: 8px;")
        layout.addWidget(self._preview)

        # OK / Cancel.
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_selection_changed(
        self, current: QListWidgetItem | None, _prev: QListWidgetItem | None
    ) -> None:
        if current is None:
            self._preview.setText("")
            return
        filename = current.data(256)
        try:
            t = load_template(filename)
            params = t.get("parameters", {})
            lines = [f"{k} = {v}" for k, v in list(params.items())[:10]]
            if len(params) > 10:
                lines.append(f"... and {len(params) - 10} more parameters")
            self._preview.setText("\n".join(lines))
        except Exception:
            self._preview.setText("(preview unavailable)")

    def selected_template(self) -> str | None:
        """Return the selected template filename, or None."""
        item = self._list.currentItem()
        if item:
            return item.data(256)
        return None
