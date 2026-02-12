"""Output file readers for REMORA simulation results."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OutputReader protocol
# ---------------------------------------------------------------------------


class OutputReader(Protocol):
    """Common interface for reading simulation output."""

    def get_variables(self) -> list[str]: ...
    def get_dimensions(self) -> dict[str, int]: ...
    def get_time_steps(self) -> list[float]: ...
    def get_coordinates(self) -> dict[str, np.ndarray]: ...
    def get_field(self, variable: str, time_index: int) -> np.ndarray: ...
    def get_slice(
        self, variable: str, time_index: int, axis: str, index: int
    ) -> np.ndarray: ...
    def get_variable_info(self, variable: str) -> dict[str, Any]: ...
    def get_statistics(self, variable: str, time_index: int) -> dict[str, float]: ...
    def close(self) -> None: ...


# ---------------------------------------------------------------------------
# NetCDFReader
# ---------------------------------------------------------------------------


class NetCDFReader:
    """Read REMORA output from NetCDF files using xarray (lazy loading)."""

    def __init__(self, path: str | Path) -> None:
        import xarray as xr

        self._path = Path(path)
        try:
            self._ds = xr.open_dataset(self._path, chunks="auto")
        except ImportError:
            # dask not installed — fall back to eager loading
            self._ds = xr.open_dataset(self._path)
        logger.info("Opened NetCDF: %s", self._path)

    def get_variables(self) -> list[str]:
        """Return names of data variables (excluding coordinates)."""
        return list(self._ds.data_vars)

    def get_dimensions(self) -> dict[str, int]:
        """Return dimension names and sizes."""
        return dict(self._ds.sizes)

    def get_time_steps(self) -> list[float]:
        """Return simulation time values."""
        if "time" in self._ds.coords:
            return [float(t) for t in self._ds.coords["time"].values]
        return []

    def get_coordinates(self) -> dict[str, np.ndarray]:
        """Return coordinate arrays for spatial dimensions."""
        result: dict[str, np.ndarray] = {}
        for name in ("x", "y", "z"):
            if name in self._ds.coords:
                result[name] = self._ds.coords[name].values
        return result

    def get_field(self, variable: str, time_index: int) -> np.ndarray:
        """Return the 3D field array for a variable at a given time step."""
        if variable not in self._ds.data_vars:
            raise KeyError(f"Variable not found: {variable}")
        var = self._ds[variable]
        n_times = var.sizes.get("time", 0)
        if time_index < 0 or time_index >= n_times:
            raise IndexError(
                f"time_index {time_index} out of range [0, {n_times})"
            )
        return var.isel(time=time_index).values

    def get_slice(
        self, variable: str, time_index: int, axis: str, index: int
    ) -> np.ndarray:
        """Return a 2D slice along an axis at a given index."""
        if axis not in ("x", "y", "z"):
            raise ValueError(f"Invalid axis: {axis!r}. Must be 'x', 'y', or 'z'.")
        field = self.get_field(variable, time_index)
        # field shape is (z, y, x)
        match axis:
            case "x":
                return field[:, :, index]  # z, y
            case "y":
                return field[:, index, :]  # z, x
            case "z":
                return field[index, :, :]  # y, x

    def get_variable_info(self, variable: str) -> dict[str, Any]:
        """Return metadata for a variable."""
        if variable not in self._ds.data_vars:
            raise KeyError(f"Variable not found: {variable}")
        var = self._ds[variable]
        return {
            "units": var.attrs.get("units", ""),
            "long_name": var.attrs.get("long_name", variable),
            "shape": var.shape,
            "dims": list(var.dims),
        }

    def get_statistics(self, variable: str, time_index: int) -> dict[str, float]:
        """Return min/max/mean for a variable at a given time step."""
        field = self.get_field(variable, time_index)
        return {
            "min": float(np.nanmin(field)),
            "max": float(np.nanmax(field)),
            "mean": float(np.nanmean(field)),
        }

    def close(self) -> None:
        """Close the underlying dataset."""
        if self._ds is not None:
            self._ds.close()
            self._ds = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# AMReXReader — header-based metadata + stub for binary reads
# ---------------------------------------------------------------------------


class AMReXReader:
    """Read REMORA output from AMReX plotfile directories.

    Parses the Header file for metadata. Full binary MultiFab reading
    is a stretch goal — for now this provides variable names, dimensions,
    and time information.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._header_path = self._path / "Header"
        if not self._header_path.exists():
            raise FileNotFoundError(
                f"Header file not found in {self._path}. "
                f"Expected AMReX plotfile directory."
            )
        self._parse_header()
        logger.info("Opened AMReX plotfile: %s", self._path)

    def _parse_header(self) -> None:
        """Parse the AMReX Header file for metadata."""
        lines = self._header_path.read_text().splitlines()
        idx = 0

        # Line 0: version string (e.g. "HyperCLaw-V1.1")
        self._version = lines[idx].strip()
        idx += 1

        # Line 1: number of variables
        self._num_vars = int(lines[idx].strip())
        idx += 1

        # Lines 2..2+num_vars: variable names
        self._variables: list[str] = []
        for _ in range(self._num_vars):
            self._variables.append(lines[idx].strip())
            idx += 1

        # Next line: number of dimensions
        self._ndim = int(lines[idx].strip())
        idx += 1

        # Next line: simulation time
        self._time = float(lines[idx].strip())
        idx += 1

        # Next line: number of levels
        self._num_levels = int(lines[idx].strip())
        idx += 1

    def get_variables(self) -> list[str]:
        return list(self._variables)

    def get_dimensions(self) -> dict[str, int]:
        return {"ndim": self._ndim, "num_levels": self._num_levels}

    def get_time_steps(self) -> list[float]:
        """Return the time from this single plotfile."""
        return [self._time]

    def get_coordinates(self) -> dict[str, np.ndarray]:
        """Coordinate extraction from AMReX requires binary reads — stub."""
        return {}

    def get_field(self, variable: str, time_index: int) -> np.ndarray:
        """Full binary MultiFab reading is not yet implemented."""
        raise NotImplementedError(
            "AMReX binary MultiFab reading is not yet implemented. "
            "Use NetCDF output format for full data access."
        )

    def get_slice(
        self, variable: str, time_index: int, axis: str, index: int
    ) -> np.ndarray:
        raise NotImplementedError(
            "AMReX binary MultiFab reading is not yet implemented."
        )

    def get_variable_info(self, variable: str) -> dict[str, Any]:
        if variable not in self._variables:
            raise KeyError(f"Variable not found: {variable}")
        return {
            "units": "",
            "long_name": variable,
            "shape": (),
            "dims": [],
        }

    def get_statistics(self, variable: str, time_index: int) -> dict[str, float]:
        raise NotImplementedError(
            "AMReX binary MultiFab reading is not yet implemented."
        )

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Auto-detect and open
# ---------------------------------------------------------------------------


def open_output(path: str | Path) -> NetCDFReader | AMReXReader:
    """Open an output file or directory, auto-detecting the format.

    - If *path* is a file with .nc/.nc4/.cdf extension → NetCDFReader
    - If *path* is a directory containing a Header file → AMReXReader
    """
    p = Path(path)
    if p.is_file() and p.suffix in (".nc", ".nc4", ".cdf"):
        return NetCDFReader(p)
    if p.is_dir() and (p / "Header").exists():
        return AMReXReader(p)
    raise ValueError(
        f"Cannot determine output format for {p}. "
        f"Expected a .nc file or an AMReX plotfile directory."
    )
