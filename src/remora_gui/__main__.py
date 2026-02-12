"""Entry point for REMORA-GUI: python -m remora_gui."""

from __future__ import annotations

import sys

from remora_gui.app import RemoraApp
from remora_gui.ui.main_window import MainWindow


def main() -> int:
    """Launch the REMORA-GUI application."""
    app = RemoraApp(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
