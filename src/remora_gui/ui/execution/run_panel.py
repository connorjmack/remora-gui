"""Run panel — machine selector, MPI config, run/stop, progress, log viewer."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from remora_gui.ui.execution.log_viewer import LogViewer


class RunPanel(QWidget):
    """Execution UI with machine selector, run/stop, progress bar, and log viewer."""

    run_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        self.setLayout(layout)

        # -- Controls row --
        controls = QHBoxLayout()
        layout.addLayout(controls)

        controls.addWidget(QLabel("Machine:"))
        self.machine_combo = QComboBox()
        self.machine_combo.addItem("Local")
        controls.addWidget(self.machine_combo)

        controls.addWidget(QLabel("MPI procs:"))
        self.mpi_spin = QSpinBox()
        self.mpi_spin.setRange(1, 1024)
        self.mpi_spin.setValue(1)
        controls.addWidget(self.mpi_spin)

        controls.addStretch()

        self.run_btn = QPushButton("Run")
        self.run_btn.setStyleSheet("background-color: #2c7a7b; font-weight: bold;")
        self.run_btn.clicked.connect(self.run_requested.emit)
        controls.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #e53e3e; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        controls.addWidget(self.stop_btn)

        # -- Status and progress --
        status_row = QHBoxLayout()
        layout.addLayout(status_row)

        self.status_label = QLabel("Ready")
        status_row.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_row.addWidget(self.progress_bar, stretch=1)

        # -- Log viewer --
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=1)

    # ---- Public helpers ----

    def set_running(self, running: bool) -> None:
        """Toggle UI between running and idle states."""
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.machine_combo.setEnabled(not running)
        self.mpi_spin.setEnabled(not running)

    def set_status(self, text: str) -> None:
        """Update the status label."""
        self.status_label.setText(text)

    def set_progress(self, step: int, max_step: int) -> None:
        """Update the progress bar."""
        if max_step > 0:
            self.progress_bar.setRange(0, max_step)
            self.progress_bar.setValue(step)
        self.set_status(f"Running (step {step}/{max_step})")

    def set_machine_profiles(self, profiles: list[dict[str, Any]]) -> None:
        """Populate machine selector from profiles."""
        self.machine_combo.clear()
        self.machine_combo.addItem("Local")
        for p in profiles:
            self.machine_combo.addItem(p.get("name", "Unknown"))
