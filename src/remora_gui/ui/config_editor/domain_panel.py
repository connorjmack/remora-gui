"""Domain config panel with computed grid resolution display."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QLabel, QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class DomainPanel(ConfigPanel):
    """Extends ConfigPanel("domain") with a computed dx/dy/dz info box."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("domain", parent)
        self._info_label = QLabel()
        self._info_label.setStyleSheet("color: #4299e1; padding: 8px;")
        # Insert info label before the stretch.
        self._layout.insertWidget(self._layout.count() - 1, self._info_label)
        self._update_info()
        self.values_changed.connect(self._on_values_changed)

    def _on_values_changed(self, values: dict[str, Any]) -> None:
        self._update_info()

    def _update_info(self) -> None:
        """Compute and display grid resolution."""
        values = self.get_values()
        prob_lo = values.get("remora.prob_lo", [0, 0, 0])
        prob_hi = values.get("remora.prob_hi", [1, 1, 1])
        n_cell = values.get("remora.n_cell", [1, 1, 1])

        parts = []
        for axis, (lo, hi, n) in enumerate(zip(prob_lo, prob_hi, n_cell, strict=True)):
            label = ["dx", "dy", "dz"][axis]
            if n > 0:
                parts.append(f"{label} = {(hi - lo) / n:.4g}")
            else:
                parts.append(f"{label} = N/A")
        self._info_label.setText("Grid resolution:  " + "    ".join(parts))
