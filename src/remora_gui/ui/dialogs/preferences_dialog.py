"""Preferences dialog — general settings, machines, editor config."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.settings import AppSettings


class PreferencesDialog(QDialog):
    """Application-wide preferences dialog."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(500, 350)
        self._settings = settings

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # -- General tab --
        general = QWidget()
        general_form = QFormLayout()
        general.setLayout(general_form)

        dir_row = QHBoxLayout()
        self._project_dir_edit = QLineEdit(str(settings.get_default_project_dir()))
        dir_row.addWidget(self._project_dir_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_project_dir)
        dir_row.addWidget(browse_btn)
        general_form.addRow("Default project dir:", dir_row)

        tabs.addTab(general, "General")

        # -- OK / Cancel --
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_project_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Default Directory", self._project_dir_edit.text()
        )
        if path:
            self._project_dir_edit.setText(path)

    def _apply_and_accept(self) -> None:
        self._settings.set_default_project_dir(self._project_dir_edit.text())
        self.accept()
