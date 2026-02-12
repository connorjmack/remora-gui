"""Config editor tab — form panels + raw editor + validation display."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.input_file import parse_input_string, write_input_string
from remora_gui.core.validator import validate
from remora_gui.ui.config_editor.advection_panel import AdvectionPanel
from remora_gui.ui.config_editor.boundary_panel import BoundaryPanel
from remora_gui.ui.config_editor.domain_panel import DomainPanel
from remora_gui.ui.config_editor.mixing_panel import MixingPanel
from remora_gui.ui.config_editor.output_panel import OutputPanel
from remora_gui.ui.config_editor.parallel_panel import ParallelPanel
from remora_gui.ui.config_editor.physics_panel import PhysicsPanel
from remora_gui.ui.config_editor.raw_editor import RawEditor
from remora_gui.ui.config_editor.timing_panel import TimingPanel


class ConfigEditorTab(QWidget):
    """Central config editing widget with form panels, raw editor, and validation."""

    values_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._syncing = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Top: splitter with form tabs on left, raw editor on right.
        self._splitter = QSplitter()
        layout.addWidget(self._splitter, stretch=1)

        # -- Form panels in a tab widget --
        self._panel_tabs = QTabWidget()
        self._panels = self._create_panels()
        for label, panel in self._panels:
            self._panel_tabs.addTab(panel, label)
            panel.values_changed.connect(self._on_form_changed)
        self._splitter.addWidget(self._panel_tabs)

        # -- Raw editor (togglable) --
        self._raw_editor = RawEditor()
        self._raw_editor.text_changed.connect(self._on_raw_changed)
        self._splitter.addWidget(self._raw_editor)
        self._raw_editor.setVisible(False)

        # Toggle button for raw editor.
        toggle_row = QHBoxLayout()
        self._toggle_btn = QPushButton("Show Raw Editor")
        self._toggle_btn.clicked.connect(self._toggle_raw_editor)
        toggle_row.addStretch()
        toggle_row.addWidget(self._toggle_btn)
        layout.addLayout(toggle_row)

        # Debounce timer for raw → form sync.
        self._raw_debounce = QTimer()
        self._raw_debounce.setSingleShot(True)
        self._raw_debounce.setInterval(500)
        self._raw_debounce.timeout.connect(self._sync_raw_to_form)

        # -- Validation panel at bottom --
        self._validation_list = QListWidget()
        self._validation_list.setMaximumHeight(120)
        layout.addWidget(QLabel("Validation"))
        layout.addWidget(self._validation_list)

        # Initial sync.
        self._sync_form_to_raw()
        self._run_validation()

    def _create_panels(self) -> list[tuple[str, Any]]:
        return [
            ("Domain", DomainPanel()),
            ("Timing", TimingPanel()),
            ("Physics", PhysicsPanel()),
            ("Mixing", MixingPanel()),
            ("BCs", BoundaryPanel()),
            ("Advection", AdvectionPanel()),
            ("Output", OutputPanel()),
            ("Parallel", ParallelPanel()),
        ]

    # ---- Sync logic ----

    def _on_form_changed(self, values: dict[str, Any]) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            self._sync_form_to_raw()
            self._run_validation()
            self.values_changed.emit(self.get_all_values())
        finally:
            self._syncing = False

    def _on_raw_changed(self, text: str) -> None:
        if self._syncing:
            return
        self._raw_debounce.start()

    def _sync_form_to_raw(self) -> None:
        """Push current form values to the raw editor."""
        params = OrderedDict(self.get_all_values())
        text = write_input_string(params)
        self._raw_editor.set_text(text)

    def _sync_raw_to_form(self) -> None:
        """Parse raw text and push values into the form panels."""
        self._syncing = True
        try:
            params = parse_input_string(self._raw_editor.get_text())
            for _label, panel in self._panels:
                panel.set_values(params)
            self._run_validation()
            self.values_changed.emit(self.get_all_values())
        except Exception:
            pass  # Incomplete/invalid text — don't crash.
        finally:
            self._syncing = False

    def _toggle_raw_editor(self) -> None:
        visible = not self._raw_editor.isVisible()
        self._raw_editor.setVisible(visible)
        self._toggle_btn.setText("Hide Raw Editor" if visible else "Show Raw Editor")
        if visible:
            self._sync_form_to_raw()

    # ---- Validation ----

    def _run_validation(self) -> None:
        """Run cross-parameter validation and update the list."""
        self._validation_list.clear()
        params = self.get_all_values()
        messages = validate(params)
        for msg in messages:
            icon = {"error": "X", "warning": "!", "info": "i"}.get(msg.level, "?")
            item = QListWidgetItem(f"[{icon}] {msg.rule_id}: {msg.message}")
            self._validation_list.addItem(item)

    # ---- Public API ----

    def get_all_values(self) -> dict[str, Any]:
        """Collect parameter values from all panels."""
        result: dict[str, Any] = {}
        for _label, panel in self._panels:
            result.update(panel.get_values())
        return result

    def set_all_values(self, params: dict[str, Any]) -> None:
        """Push a parameter dict into all panels."""
        self._syncing = True
        try:
            for _label, panel in self._panels:
                panel.set_values(params)
            self._sync_form_to_raw()
            self._run_validation()
        finally:
            self._syncing = False

    def reset_to_defaults(self) -> None:
        """Reset all panels to schema defaults."""
        for _label, panel in self._panels:
            panel.reset_to_defaults()
        self._sync_form_to_raw()
        self._run_validation()
