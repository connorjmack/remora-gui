"""Three-component vector widget for int_vec3 and float_vec3 parameters."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QWidget,
)


class Vector3Widget(QWidget):
    """Row of three spin boxes labelled x / y / z."""

    value_changed = pyqtSignal(list)

    def __init__(
        self,
        float_mode: bool = True,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._float_mode = float_mode

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self._boxes: list[QDoubleSpinBox | QSpinBox] = []
        for label_text in ("x", "y", "z"):
            layout.addWidget(QLabel(label_text))
            if float_mode:
                box = QDoubleSpinBox()
                box.setDecimals(6)
                box.setRange(
                    min_value if min_value is not None else -1e15,
                    max_value if max_value is not None else 1e15,
                )
                box.valueChanged.connect(self._emit_value)
            else:
                box = QSpinBox()
                box.setRange(
                    int(min_value) if min_value is not None else -999999,
                    int(max_value) if max_value is not None else 999999,
                )
                box.valueChanged.connect(self._emit_value)
            self._boxes.append(box)
            layout.addWidget(box)

    def value(self) -> list[float] | list[int]:
        """Return current [x, y, z] values."""
        if self._float_mode:
            return [b.value() for b in self._boxes]
        return [int(b.value()) for b in self._boxes]

    def set_value(self, values: list[float | int]) -> None:
        """Set all three components, silently clamped to range."""
        for box, val in zip(self._boxes, values, strict=True):
            box.blockSignals(True)
            box.setValue(val)
            box.blockSignals(False)
        self._emit_value()

    def _emit_value(self) -> None:
        self.value_changed.emit(self.value())
