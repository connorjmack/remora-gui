"""Boundary conditions config panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class BoundaryPanel(ConfigPanel):
    """Config panel for the boundary parameter group — 6 face dropdowns."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("boundary", parent)
