"""New Project dialog — name, description, directory, template selection."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.templates import list_templates


class NewProjectDialog(QDialog):
    """Dialog for creating a new REMORA project."""

    def __init__(self, default_dir: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()
        self.setLayout(layout)

        form = QFormLayout()
        layout.addLayout(form)

        # Project name.
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Simulation")
        form.addRow("Name:", self.name_edit)

        # Description.
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("Optional description...")
        form.addRow("Description:", self.desc_edit)

        # Base directory.
        dir_row = QHBoxLayout()
        self.dir_edit = QLineEdit(default_dir or str(Path.home() / "remora_projects"))
        dir_row.addWidget(self.dir_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        form.addRow("Directory:", dir_row)

        # Template selector.
        self.template_combo = QComboBox()
        self.template_combo.addItem("(None)", "")
        for t in list_templates():
            self.template_combo.addItem(f"{t['name']} — {t['description']}", t["file"])
        form.addRow("Template:", self.template_combo)

        # OK / Cancel.
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def project_name(self) -> str:
        return self.name_edit.text().strip()

    def project_description(self) -> str:
        return self.desc_edit.toPlainText().strip()

    def base_directory(self) -> str:
        return self.dir_edit.text().strip()

    def selected_template(self) -> str:
        """Return the template filename or empty string for none."""
        return self.template_combo.currentData() or ""
