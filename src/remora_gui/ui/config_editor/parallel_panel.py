"""Parallel config panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class ParallelPanel(ConfigPanel):
    """Config panel for the parallel parameter group."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("parallel", parent)
