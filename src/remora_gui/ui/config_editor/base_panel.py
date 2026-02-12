"""Base config panel that auto-generates widgets from the parameter schema."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QScrollArea, QVBoxLayout, QWidget

from remora_gui.core.parameter_schema import PARAMETER_SCHEMA
from remora_gui.ui.widgets.parameter_widget import ParameterWidget


class ConfigPanel(QScrollArea):
    """Scroll area that auto-generates ParameterWidgets for a schema group.

    Subclass to add custom computed fields or layout tweaks.
    """

    values_changed = pyqtSignal(dict)

    def __init__(self, group_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._group_name = group_name
        self._widgets: dict[str, ParameterWidget] = {}

        # Scroll area setup.
        self.setWidgetResizable(True)
        container = QWidget()
        self._layout = QVBoxLayout()
        container.setLayout(self._layout)
        self.setWidget(container)

        # Build widgets from schema.
        form = QFormLayout()
        self._layout.addLayout(form)

        for param in PARAMETER_SCHEMA.get(group_name, []):
            pw = ParameterWidget(param)
            pw.value_changed.connect(self._on_widget_changed)
            self._widgets[param.key] = pw
            form.addRow(pw)

        self._layout.addStretch()

        # Wire depends_on visibility.
        self._setup_dependencies()

    def _setup_dependencies(self) -> None:
        """Hide/show widgets based on depends_on relationships."""
        for _key, pw in self._widgets.items():
            if pw.param.depends_on:
                for dep_key, dep_value in pw.param.depends_on.items():
                    dep_widget = self._widgets.get(dep_key)
                    if dep_widget is not None:
                        dep_widget.value_changed.connect(
                            lambda _k, _v, target=pw, dk=dep_key, dv=dep_value:
                                self._update_visibility(target, dk, dv)
                        )
                # Initial visibility.
                self._check_visibility(pw)

    def _check_visibility(self, pw: ParameterWidget) -> None:
        """Set initial visibility based on current dependency values."""
        if not pw.param.depends_on:
            return
        for dep_key, dep_value in pw.param.depends_on.items():
            dep_widget = self._widgets.get(dep_key)
            if dep_widget is not None and dep_widget.value() != dep_value:
                pw.setVisible(False)
                return
        pw.setVisible(True)

    def _update_visibility(self, target: ParameterWidget, dep_key: str, dep_value: Any) -> None:
        """Re-check visibility of a dependent widget."""
        self._check_visibility(target)

    def _on_widget_changed(self, key: str, value: Any) -> None:
        self.values_changed.emit(self.get_values())

    # ---- Public API ----

    def get_values(self) -> dict[str, Any]:
        """Collect all current parameter values."""
        return {key: pw.value() for key, pw in self._widgets.items()}

    def set_values(self, params: dict[str, Any]) -> None:
        """Populate widgets from a parameter dict."""
        for key, value in params.items():
            pw = self._widgets.get(key)
            if pw is not None:
                pw.set_value(value)
        # Re-check all dependencies after bulk update.
        for pw in self._widgets.values():
            self._check_visibility(pw)

    def reset_to_defaults(self) -> None:
        """Reset all widgets to their schema defaults."""
        for pw in self._widgets.values():
            if pw.param.default is not None:
                pw.set_value(pw.param.default)
        for pw in self._widgets.values():
            self._check_visibility(pw)
        self.values_changed.emit(self.get_values())

    def get_widget(self, key: str) -> ParameterWidget | None:
        """Return the ParameterWidget for a given key, or None."""
        return self._widgets.get(key)
