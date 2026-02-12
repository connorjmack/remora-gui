"""2D slice viewer — matplotlib canvas with variable/time/axis/slice controls."""

from __future__ import annotations

from typing import Any, ClassVar

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.output_reader import OutputReader


class SliceViewer(QWidget):
    """Interactive 2D slice viewer with matplotlib embedding."""

    # Emitted when the user clicks on the plot: (x_coord, y_coord)
    point_clicked = pyqtSignal(float, float)

    _COLORMAPS: ClassVar[list[str]] = [
        "viridis", "plasma", "inferno", "magma", "cividis", "coolwarm", "RdBu_r", "jet",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: OutputReader | None = None
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(100)
        self._debounce_timer.timeout.connect(self._update_plot)

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # --- Controls row ---
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Variable:"))
        self._var_combo = QComboBox()
        self._var_combo.currentTextChanged.connect(self._on_control_changed)
        controls.addWidget(self._var_combo)

        controls.addWidget(QLabel("Time:"))
        self._time_slider = QSlider()
        self._time_slider.setOrientation(1)  # Horizontal
        self._time_slider.setMinimum(0)
        self._time_slider.valueChanged.connect(self._on_control_changed)
        controls.addWidget(self._time_slider)
        self._time_label = QLabel("0")
        self._time_label.setMinimumWidth(60)
        controls.addWidget(self._time_label)

        controls.addWidget(QLabel("Axis:"))
        self._axis_combo = QComboBox()
        self._axis_combo.addItems(["x", "y", "z"])
        self._axis_combo.setCurrentText("z")
        self._axis_combo.currentTextChanged.connect(self._on_axis_changed)
        controls.addWidget(self._axis_combo)

        controls.addWidget(QLabel("Slice:"))
        self._slice_slider = QSlider()
        self._slice_slider.setOrientation(1)
        self._slice_slider.setMinimum(0)
        self._slice_slider.valueChanged.connect(self._on_control_changed)
        controls.addWidget(self._slice_slider)
        self._slice_label = QLabel("0")
        self._slice_label.setMinimumWidth(40)
        controls.addWidget(self._slice_label)

        layout.addLayout(controls)

        # --- Colormap row ---
        cmap_row = QHBoxLayout()

        cmap_row.addWidget(QLabel("Colormap:"))
        self._cmap_combo = QComboBox()
        self._cmap_combo.addItems(self._COLORMAPS)
        self._cmap_combo.currentTextChanged.connect(self._on_control_changed)
        cmap_row.addWidget(self._cmap_combo)

        cmap_row.addWidget(QLabel("Min:"))
        self._vmin_spin = QDoubleSpinBox()
        self._vmin_spin.setDecimals(4)
        self._vmin_spin.setRange(-1e12, 1e12)
        self._vmin_spin.setSpecialValueText("auto")
        self._vmin_spin.setValue(self._vmin_spin.minimum())
        self._vmin_spin.valueChanged.connect(self._on_control_changed)
        cmap_row.addWidget(self._vmin_spin)

        cmap_row.addWidget(QLabel("Max:"))
        self._vmax_spin = QDoubleSpinBox()
        self._vmax_spin.setDecimals(4)
        self._vmax_spin.setRange(-1e12, 1e12)
        self._vmax_spin.setSpecialValueText("auto")
        self._vmax_spin.setValue(self._vmax_spin.minimum())
        self._vmax_spin.valueChanged.connect(self._on_control_changed)
        cmap_row.addWidget(self._vmax_spin)

        cmap_row.addStretch()
        layout.addLayout(cmap_row)

        # --- Matplotlib canvas ---
        self._figure = Figure(figsize=(8, 6), dpi=100)
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.mpl_connect("button_press_event", self._on_canvas_click)
        layout.addWidget(self._canvas, stretch=1)

        # --- Navigation toolbar ---
        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        layout.addWidget(self._toolbar)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_reader(self, reader: OutputReader) -> None:
        """Load an output reader and populate controls."""
        self._reader = reader
        variables = reader.get_variables()
        self._var_combo.blockSignals(True)
        self._var_combo.clear()
        self._var_combo.addItems(variables)
        self._var_combo.blockSignals(False)

        times = reader.get_time_steps()
        self._time_slider.blockSignals(True)
        self._time_slider.setMaximum(max(0, len(times) - 1))
        self._time_slider.setValue(0)
        self._time_slider.blockSignals(False)

        self._update_slice_range()
        self._update_plot()

    def current_variable(self) -> str:
        return self._var_combo.currentText()

    def current_time_index(self) -> int:
        return self._time_slider.value()

    def current_axis(self) -> str:
        return self._axis_combo.currentText()

    def current_slice_index(self) -> int:
        return self._slice_slider.value()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_control_changed(self) -> None:
        """Debounce control changes."""
        self._time_label.setText(str(self._time_slider.value()))
        self._slice_label.setText(str(self._slice_slider.value()))
        self._debounce_timer.start()

    def _on_axis_changed(self) -> None:
        self._update_slice_range()
        self._on_control_changed()

    def _update_slice_range(self) -> None:
        """Update the slice slider range based on current axis."""
        if self._reader is None:
            return
        dims = self._reader.get_dimensions()
        axis = self._axis_combo.currentText()
        max_idx = dims.get(axis, 1) - 1
        self._slice_slider.blockSignals(True)
        self._slice_slider.setMaximum(max(0, max_idx))
        self._slice_slider.setValue(min(self._slice_slider.value(), max_idx))
        self._slice_slider.blockSignals(False)

    def _on_canvas_click(self, event: Any) -> None:
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self.point_clicked.emit(float(event.xdata), float(event.ydata))

    # ------------------------------------------------------------------
    # Plot rendering
    # ------------------------------------------------------------------

    def _update_plot(self) -> None:
        """Render the current slice."""
        if self._reader is None:
            return

        var = self._var_combo.currentText()
        if not var:
            return

        time_idx = self._time_slider.value()
        axis = self._axis_combo.currentText()
        slice_idx = self._slice_slider.value()

        try:
            data = self._reader.get_slice(var, time_idx, axis, slice_idx)
        except (KeyError, IndexError, NotImplementedError):
            return

        self._figure.clear()
        ax = self._figure.add_subplot(111)

        # Determine axis labels and coordinate arrays
        coords = self._reader.get_coordinates()
        axis_map = {"x": ("y", "z"), "y": ("x", "z"), "z": ("x", "y")}
        h_name, v_name = axis_map[axis]

        # Determine vmin/vmax
        vmin_val = self._vmin_spin.value()
        vmin = None if vmin_val == self._vmin_spin.minimum() else vmin_val
        vmax_val = self._vmax_spin.value()
        vmax = None if vmax_val == self._vmax_spin.minimum() else vmax_val

        cmap = self._cmap_combo.currentText()

        # Plot
        if h_name in coords and v_name in coords:
            h_coords = coords[h_name]
            v_coords = coords[v_name]
            im = ax.pcolormesh(h_coords, v_coords, data, cmap=cmap, vmin=vmin, vmax=vmax)
        else:
            im = ax.imshow(
                data, origin="lower", aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax
            )

        # Labels and title
        ax.set_xlabel(h_name)
        ax.set_ylabel(v_name)

        info = self._reader.get_variable_info(var)
        units = info.get("units", "")
        times = self._reader.get_time_steps()
        time_val = times[time_idx] if time_idx < len(times) else 0
        title = f"{var}"
        if units:
            title += f" [{units}]"
        title += f"  |  {axis}={slice_idx}  |  t={time_val}"
        ax.set_title(title)

        self._figure.colorbar(im, ax=ax, label=units)
        self._figure.tight_layout()
        self._canvas.draw_idle()
