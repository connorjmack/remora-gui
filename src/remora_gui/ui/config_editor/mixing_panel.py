"""Mixing config panel — GLS params hidden when mixing_type != gls."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from remora_gui.ui.config_editor.base_panel import ConfigPanel


class MixingPanel(ConfigPanel):
    """Config panel for the mixing parameter group.

    GLS sub-parameters are automatically hidden/shown via depends_on in the schema.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("mixing", parent)
