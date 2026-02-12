"""Advection config panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class AdvectionPanel(ConfigPanel):
    """Config panel for the advection parameter group."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("advection", parent)
