"""Output tab — file picker, variable explorer, slice viewer, time series."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.output_reader import OutputReader, open_output
from remora_gui.ui.visualization.slice_viewer import SliceViewer
from remora_gui.ui.visualization.timeseries_viewer import TimeSeriesViewer
from remora_gui.ui.visualization.variable_explorer import VariableExplorer


class OutputTab(QWidget):
    """Main output/visualization tab assembling all viewers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: OutputReader | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        # --- File picker row ---
        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Output:"))

        self._path_label = QLabel("No output loaded")
        self._path_label.setStyleSheet("color: #a0aec0;")
        picker_row.addWidget(self._path_label, stretch=1)

        self._open_file_btn = QPushButton("Open File...")
        self._open_file_btn.clicked.connect(self._on_open_file)
        picker_row.addWidget(self._open_file_btn)

        self._open_dir_btn = QPushButton("Open Directory...")
        self._open_dir_btn.clicked.connect(self._on_open_dir)
        picker_row.addWidget(self._open_dir_btn)

        layout.addLayout(picker_row)

        # --- Main content: splitter with variable explorer + viewers ---
        splitter = QSplitter()
        layout.addWidget(splitter, stretch=1)

        # Left: variable explorer
        self._var_explorer = VariableExplorer()
        self._var_explorer.variable_selected.connect(self._on_variable_selected)
        splitter.addWidget(self._var_explorer)

        # Right: tabbed viewers
        viewer_tabs = QTabWidget()
        self._slice_viewer = SliceViewer()
        self._timeseries_viewer = TimeSeriesViewer()

        viewer_tabs.addTab(self._slice_viewer, "Slice View")
        viewer_tabs.addTab(self._timeseries_viewer, "Time Series")
        splitter.addWidget(viewer_tabs)

        splitter.setSizes([300, 700])

        # Connect slice viewer click to time series probe
        self._slice_viewer.point_clicked.connect(self._on_slice_clicked)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_output(self, path: str | Path) -> None:
        """Open an output file/directory and populate all viewers."""
        try:
            reader = open_output(path)
        except (ValueError, FileNotFoundError, OSError) as exc:
            QMessageBox.warning(self, "Open Output", str(exc))
            return

        self._reader = reader
        self._path_label.setText(str(path))
        self._var_explorer.set_reader(reader)
        self._slice_viewer.set_reader(reader)
        self._timeseries_viewer.set_reader(reader)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Output File", "", "NetCDF Files (*.nc *.nc4 *.cdf);;All Files (*)"
        )
        if path:
            self.load_output(path)

    def _on_open_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open AMReX Plotfile Directory")
        if path:
            self.load_output(path)

    def _on_variable_selected(self, variable: str) -> None:
        """When user double-clicks a variable, show it in the slice viewer."""
        idx = self._slice_viewer._var_combo.findText(variable)
        if idx >= 0:
            self._slice_viewer._var_combo.setCurrentIndex(idx)

    def _on_slice_clicked(self, x: float, y: float) -> None:
        """When user clicks on the slice viewer, update the time series probe."""
        if self._reader is None:
            return
        coords = self._reader.get_coordinates()
        # Find nearest indices
        ix = _nearest_index(coords.get("x"), x)
        iy = _nearest_index(coords.get("y"), y)
        iz = self._slice_viewer.current_slice_index()
        axis = self._slice_viewer.current_axis()

        # Map click coordinates to proper i/j/k based on current axis
        match axis:
            case "x":
                # Click on (y, z) plane
                iy = _nearest_index(coords.get("y"), x)
                iz = _nearest_index(coords.get("z"), y)
                ix = self._slice_viewer.current_slice_index()
            case "y":
                ix = _nearest_index(coords.get("x"), x)
                iz = _nearest_index(coords.get("z"), y)
                iy = self._slice_viewer.current_slice_index()
            case "z":
                ix = _nearest_index(coords.get("x"), x)
                iy = _nearest_index(coords.get("y"), y)
                iz = self._slice_viewer.current_slice_index()

        self._timeseries_viewer.set_probe_point(ix, iy, iz)


def _nearest_index(coords: object, value: float) -> int:
    """Find the index of the nearest coordinate value."""
    import numpy as np

    if coords is None or not hasattr(coords, "__len__") or len(coords) == 0:
        return 0
    arr = np.asarray(coords)
    return int(np.argmin(np.abs(arr - value)))
