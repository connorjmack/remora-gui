"""Time series viewer — plot variable value at a point over all time steps."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.output_reader import OutputReader


class TimeSeriesViewer(QWidget):
    """Plot a variable's value at a fixed point across all time steps."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._reader: OutputReader | None = None
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        controls = QHBoxLayout()

        controls.addWidget(QLabel("Variable:"))
        self._var_combo = QComboBox()
        controls.addWidget(self._var_combo)

        controls.addWidget(QLabel("i:"))
        self._ix_spin = QSpinBox()
        self._ix_spin.setMinimum(0)
        controls.addWidget(self._ix_spin)

        controls.addWidget(QLabel("j:"))
        self._iy_spin = QSpinBox()
        self._iy_spin.setMinimum(0)
        controls.addWidget(self._iy_spin)

        controls.addWidget(QLabel("k:"))
        self._iz_spin = QSpinBox()
        self._iz_spin.setMinimum(0)
        controls.addWidget(self._iz_spin)

        controls.addStretch()
        layout.addLayout(controls)

        # Second variable for dual y-axis overlay
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("Overlay:"))
        self._overlay_combo = QComboBox()
        self._overlay_combo.addItem("(none)")
        overlay_row.addWidget(self._overlay_combo)
        overlay_row.addStretch()
        layout.addLayout(overlay_row)

        self._figure = Figure(figsize=(8, 4), dpi=100)
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout.addWidget(self._canvas, stretch=1)

        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        layout.addWidget(self._toolbar)

        # Connect signals
        self._var_combo.currentTextChanged.connect(self._update_plot)
        self._overlay_combo.currentTextChanged.connect(self._update_plot)
        self._ix_spin.valueChanged.connect(self._update_plot)
        self._iy_spin.valueChanged.connect(self._update_plot)
        self._iz_spin.valueChanged.connect(self._update_plot)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_reader(self, reader: OutputReader) -> None:
        """Load a reader and populate variable list."""
        self._reader = reader
        variables = reader.get_variables()

        self._var_combo.blockSignals(True)
        self._var_combo.clear()
        self._var_combo.addItems(variables)
        self._var_combo.blockSignals(False)

        self._overlay_combo.blockSignals(True)
        self._overlay_combo.clear()
        self._overlay_combo.addItem("(none)")
        self._overlay_combo.addItems(variables)
        self._overlay_combo.blockSignals(False)

        dims = reader.get_dimensions()
        self._ix_spin.setMaximum(dims.get("x", 1) - 1)
        self._iy_spin.setMaximum(dims.get("y", 1) - 1)
        self._iz_spin.setMaximum(dims.get("z", 1) - 1)

        self._update_plot()

    def set_probe_point(self, ix: int, iy: int, iz: int) -> None:
        """Set the probe location (e.g. from a click on the slice viewer)."""
        self._ix_spin.setValue(ix)
        self._iy_spin.setValue(iy)
        self._iz_spin.setValue(iz)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def _update_plot(self) -> None:
        if self._reader is None:
            return

        var = self._var_combo.currentText()
        if not var:
            return

        times = self._reader.get_time_steps()
        if not times:
            return

        ix = self._ix_spin.value()
        iy = self._iy_spin.value()
        iz = self._iz_spin.value()

        # Extract value at (ix, iy, iz) for each time step
        values: list[float] = []
        for t_idx in range(len(times)):
            try:
                field = self._reader.get_field(var, t_idx)
                values.append(float(field[iz, iy, ix]))
            except (IndexError, NotImplementedError):
                values.append(float("nan"))

        self._figure.clear()
        ax = self._figure.add_subplot(111)

        info = self._reader.get_variable_info(var)
        units = info.get("units", "")
        label = f"{var} [{units}]" if units else var

        ax.plot(times, values, "o-", label=label, color="#4299e1")
        ax.set_xlabel("Time")
        ax.set_ylabel(label)
        ax.set_title(f"Time series at ({ix}, {iy}, {iz})")
        ax.grid(True, alpha=0.3)

        # Overlay second variable on dual y-axis
        overlay_var = self._overlay_combo.currentText()
        if overlay_var and overlay_var != "(none)" and overlay_var != var:
            overlay_values: list[float] = []
            for t_idx in range(len(times)):
                try:
                    field = self._reader.get_field(overlay_var, t_idx)
                    overlay_values.append(float(field[iz, iy, ix]))
                except (IndexError, NotImplementedError):
                    overlay_values.append(float("nan"))

            ax2 = ax.twinx()
            o_info = self._reader.get_variable_info(overlay_var)
            o_units = o_info.get("units", "")
            o_label = f"{overlay_var} [{o_units}]" if o_units else overlay_var
            ax2.plot(times, overlay_values, "s--", label=o_label, color="#e53e3e")
            ax2.set_ylabel(o_label)

            # Combined legend
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="best")
        else:
            ax.legend(loc="best")

        self._figure.tight_layout()
        self._canvas.draw_idle()
