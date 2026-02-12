"""Factory widget that creates the appropriate input for a REMORAParameter."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from remora_gui.core.parameter_schema import REMORAParameter
from remora_gui.ui.widgets.enum_combo import EnumComboBox
from remora_gui.ui.widgets.vector3_widget import Vector3Widget


class ScientificSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that displays values in scientific notation when appropriate."""

    def textFromValue(self, value: float) -> str:
        if value != 0.0 and (abs(value) >= 1e6 or abs(value) < 1e-3):
            return f"{value:.6e}"
        return super().textFromValue(value)

    def valueFromText(self, text: str) -> float:
        try:
            return float(text)
        except ValueError:
            return self.value()


class ParameterWidget(QWidget):
    """Auto-generated input row for a single REMORA parameter.

    Layout: label | input widget.
    Emits ``value_changed(key, value)`` on any user edit.
    """

    value_changed = pyqtSignal(str, object)

    def __init__(self, param: REMORAParameter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._param = param

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Label.
        self._label = QLabel(param.label)
        self._label.setMinimumWidth(180)
        layout.addWidget(self._label)

        # Build tooltip.
        tip_parts = [param.description]
        if param.units:
            tip_parts.append(f"Units: {param.units}")
        if param.min_value is not None or param.max_value is not None:
            lo = param.min_value if param.min_value is not None else "-inf"
            hi = param.max_value if param.max_value is not None else "inf"
            tip_parts.append(f"Range: [{lo}, {hi}]")
        self.setToolTip("\n".join(tip_parts))

        # Create the right input widget for the dtype.
        self._input: QWidget = self._make_input(param)
        layout.addWidget(self._input, stretch=1)

        # Set default value if provided.
        if param.default is not None:
            self.set_value(param.default)

    # ---- Factory ----

    def _make_input(self, param: REMORAParameter) -> QWidget:
        match param.dtype:
            case "int":
                box = QSpinBox()
                box.setRange(
                    int(param.min_value) if param.min_value is not None else -999999,
                    int(param.max_value) if param.max_value is not None else 999999,
                )
                box.valueChanged.connect(lambda v: self.value_changed.emit(param.key, v))
                return box

            case "float":
                box = ScientificSpinBox()
                box.setDecimals(8)
                box.setRange(
                    param.min_value if param.min_value is not None else -1e15,
                    param.max_value if param.max_value is not None else 1e15,
                )
                box.valueChanged.connect(lambda v: self.value_changed.emit(param.key, v))
                return box

            case "bool":
                cb = QCheckBox()
                cb.toggled.connect(lambda v: self.value_changed.emit(param.key, v))
                return cb

            case "string":
                le = QLineEdit()
                le.textChanged.connect(lambda v: self.value_changed.emit(param.key, v))
                return le

            case "enum":
                combo = EnumComboBox(param.enum_options or [])
                combo.enum_value_changed.connect(
                    lambda v: self.value_changed.emit(param.key, v)
                )
                return combo

            case "int_vec3":
                vec = Vector3Widget(
                    float_mode=False,
                    min_value=param.min_value,
                    max_value=param.max_value,
                )
                vec.value_changed.connect(lambda v: self.value_changed.emit(param.key, v))
                return vec

            case "float_vec3":
                vec = Vector3Widget(
                    float_mode=True,
                    min_value=param.min_value,
                    max_value=param.max_value,
                )
                vec.value_changed.connect(lambda v: self.value_changed.emit(param.key, v))
                return vec

            case "string_list":
                le = QLineEdit()
                le.setPlaceholderText("space-separated values")
                le.textChanged.connect(
                    lambda text: self.value_changed.emit(param.key, text.split())
                )
                return le

            case _:
                le = QLineEdit()
                le.textChanged.connect(lambda v: self.value_changed.emit(param.key, v))
                return le

    # ---- Public API ----

    def value(self) -> Any:
        """Return the current value from the input widget."""
        match self._param.dtype:
            case "int":
                return self._input.value()  # type: ignore[union-attr]
            case "float":
                return self._input.value()  # type: ignore[union-attr]
            case "bool":
                return self._input.isChecked()  # type: ignore[union-attr]
            case "string":
                return self._input.text()  # type: ignore[union-attr]
            case "enum":
                return self._input.value()  # type: ignore[union-attr]
            case "int_vec3" | "float_vec3":
                return self._input.value()  # type: ignore[union-attr]
            case "string_list":
                text = self._input.text()  # type: ignore[union-attr]
                return text.split() if text else []
            case _:
                return self._input.text()  # type: ignore[union-attr]

    def set_value(self, value: Any) -> None:
        """Programmatically set the widget value (blocks intermediate signals)."""
        self._input.blockSignals(True)
        try:
            match self._param.dtype:
                case "int":
                    self._input.setValue(value)  # type: ignore[union-attr]
                case "float":
                    self._input.setValue(value)  # type: ignore[union-attr]
                case "bool":
                    self._input.setChecked(value)  # type: ignore[union-attr]
                case "string":
                    self._input.setText(str(value))  # type: ignore[union-attr]
                case "enum":
                    self._input.set_value(str(value))  # type: ignore[union-attr]
                case "int_vec3" | "float_vec3":
                    self._input.set_value(value)  # type: ignore[union-attr]
                case "string_list":
                    text = " ".join(str(v) for v in value) if isinstance(value, list) else value
                    self._input.setText(text)  # type: ignore[union-attr]
                case _:
                    self._input.setText(str(value))  # type: ignore[union-attr]
        finally:
            self._input.blockSignals(False)

    @property
    def param(self) -> REMORAParameter:
        """The parameter definition this widget represents."""
        return self._param
