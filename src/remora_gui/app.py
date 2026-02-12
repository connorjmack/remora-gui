"""Application setup for REMORA-GUI."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

_RESOURCES_DIR = Path(__file__).parent / "resources"


class RemoraApp:
    """Wrapper around QApplication that configures the REMORA-GUI environment."""

    def __init__(self, argv: list[str] | None = None) -> None:
        self.qapp = QApplication(argv or sys.argv)
        self.qapp.setApplicationName("REMORA-GUI")
        self.qapp.setOrganizationName("REMORA")
        self.qapp.setOrganizationDomain("github.com/seahorce-scidac/REMORA")
        self.qapp.setStyle("Fusion")
        self._load_stylesheet()

    def _load_stylesheet(self) -> None:
        """Load the dark ocean theme from style.qss."""
        qss_path = _RESOURCES_DIR / "style.qss"
        if qss_path.exists():
            self.qapp.setStyleSheet(qss_path.read_text())

    def exec(self) -> int:
        """Run the Qt event loop and return the exit code."""
        return self.qapp.exec()
