"""Sweep configuration dialog — define parameter ranges and generate runs."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.parameter_schema import PARAMETER_SCHEMA
from remora_gui.core.sweep import SweepAxis


class _AxisWidget(QGroupBox):
    """Widget for configuring one sweep axis."""

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(f"Axis {index + 1}", parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        form = QFormLayout()
        self.setLayout(form)

        self._param_combo = QComboBox()
        all_keys: list[str] = []
        for params in PARAMETER_SCHEMA.values():
            all_keys.extend(p.key for p in params)
        self._param_combo.addItems(sorted(all_keys))
        form.addRow("Parameter:", self._param_combo)

        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(-1e12, 1e12)
        self._start_spin.setDecimals(6)
        form.addRow("Start:", self._start_spin)

        self._end_spin = QDoubleSpinBox()
        self._end_spin.setRange(-1e12, 1e12)
        self._end_spin.setDecimals(6)
        form.addRow("End:", self._end_spin)

        self._step_spin = QDoubleSpinBox()
        self._step_spin.setRange(1e-12, 1e12)
        self._step_spin.setDecimals(6)
        self._step_spin.setValue(1.0)
        form.addRow("Step:", self._step_spin)

        self._explicit_edit = QLineEdit()
        self._explicit_edit.setPlaceholderText("e.g. 0.001 0.01 0.1 (space-separated)")
        form.addRow("Or explicit:", self._explicit_edit)

    def get_axis(self) -> SweepAxis | None:
        """Return a SweepAxis from the widget state, or None if unconfigured."""
        key = self._param_combo.currentText()
        if not key:
            return None

        explicit_text = self._explicit_edit.text().strip()
        if explicit_text:
            try:
                values = [float(v) for v in explicit_text.split()]
            except ValueError:
                values = explicit_text.split()
            return SweepAxis(key=key, explicit=values)

        return SweepAxis(
            key=key,
            start=self._start_spin.value(),
            end=self._end_spin.value(),
            step=self._step_spin.value(),
        )


class SweepDialog(QDialog):
    """Dialog for configuring a parameter sweep."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Parameter Sweep")
        self.resize(600, 600)
        self._axis_widgets: list[_AxisWidget] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Axis widgets (start with 1, can add up to 3)
        self._axes_layout = QVBoxLayout()
        layout.addLayout(self._axes_layout)
        self._add_axis()

        add_btn = QPushButton("+ Add Axis")
        add_btn.clicked.connect(self._add_axis)
        layout.addWidget(add_btn)

        # Name template
        form = QFormLayout()
        self._name_template = QLineEdit()
        self._name_template.setPlaceholderText(
            "e.g. sweep_dt{remora.fixed_dt}_visc{remora.Akv_bak}"
        )
        form.addRow("Name template:", self._name_template)

        self._max_concurrent = QSpinBox()
        self._max_concurrent.setRange(1, 64)
        self._max_concurrent.setValue(1)
        form.addRow("Max concurrent:", self._max_concurrent)
        layout.addLayout(form)

        # Count label
        self._count_label = QLabel("Total runs: 0")
        layout.addWidget(self._count_label)

        # OK / Cancel
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("Generate")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _add_axis(self) -> None:
        if len(self._axis_widgets) >= 3:
            return
        w = _AxisWidget(len(self._axis_widgets))
        self._axis_widgets.append(w)
        self._axes_layout.addWidget(w)

    def get_axes(self) -> list[SweepAxis]:
        """Return configured sweep axes."""
        axes: list[SweepAxis] = []
        for w in self._axis_widgets:
            axis = w.get_axis()
            if axis is not None:
                axes.append(axis)
        return axes

    def name_template(self) -> str:
        """Return the name template string."""
        return self._name_template.text().strip()

    def max_concurrent(self) -> int:
        """Return the max concurrent runs setting."""
        return self._max_concurrent.value()
