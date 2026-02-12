"""Timing config panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class TimingPanel(ConfigPanel):
    """Config panel for the timing parameter group."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("timing", parent)
