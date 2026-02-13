"""Output file readers for REMORA simulation results."""

from __future__ import annotations

import logging
import re
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
# AMReXReader — reads AMReX plotfile directories (Header + binary MultiFab)
# ---------------------------------------------------------------------------

_FAB_HEADER_RE = re.compile(
    r"FAB\s+\(\((\d+),.*?\)\)"  # byte size
    r".*?"
    r"\(\((\d+),(\d+),(\d+)\)\s+\((\d+),(\d+),(\d+)\)"  # box lo/hi
    r".*?\)\s+"
    r"(\d+)"  # ncomp
)


class AMReXReader:
    """Read REMORA output from AMReX plotfile directories.

    Reads the Header for metadata and the binary Cell_D files for field data.
    Supports single-level (level 0) plotfiles.
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
        self._field_cache: dict[str, np.ndarray] = {}
        logger.info("Opened AMReX plotfile: %s", self._path)

    def _parse_header(self) -> None:
        """Parse the AMReX Header file for metadata."""
        lines = self._header_path.read_text().splitlines()
        idx = 0

        self._version = lines[idx].strip()
        idx += 1

        self._num_vars = int(lines[idx].strip())
        idx += 1

        self._variables: list[str] = []
        for _ in range(self._num_vars):
            self._variables.append(lines[idx].strip())
            idx += 1

        self._ndim = int(lines[idx].strip())
        idx += 1

        self._time = float(lines[idx].strip())
        idx += 1

        self._max_level = int(lines[idx].strip())
        idx += 1

        # Domain lo/hi
        lo = [float(v) for v in lines[idx].strip().split()]
        idx += 1
        hi = [float(v) for v in lines[idx].strip().split()]
        idx += 1
        self._prob_lo = lo
        self._prob_hi = hi

        # Skip refinement ratios (empty for single-level)
        idx += 1

        # Box layout line: e.g. "((0,0,0) (40,79,15) (0,0,0))"
        box_line = lines[idx].strip()
        idx += 1
        box_match = re.search(
            r"\((\d+),(\d+),(\d+)\)\s+\((\d+),(\d+),(\d+)\)", box_line
        )
        if box_match:
            lo_i = [int(box_match.group(i)) for i in (1, 2, 3)]
            hi_i = [int(box_match.group(i)) for i in (4, 5, 6)]
            self._nx = hi_i[0] - lo_i[0] + 1
            self._ny = hi_i[1] - lo_i[1] + 1
            self._nz = hi_i[2] - lo_i[2] + 1
        else:
            self._nx = self._ny = self._nz = 1

        # Skip to cell sizes line
        idx += 1  # step numbers
        cell_line = lines[idx].strip()
        cell_sizes = [float(v) for v in cell_line.split()]
        self._dx = cell_sizes[0] if len(cell_sizes) > 0 else 1.0
        self._dy = cell_sizes[1] if len(cell_sizes) > 1 else 1.0
        self._dz = cell_sizes[2] if len(cell_sizes) > 2 else 1.0

    def _read_fab_data(self) -> np.ndarray:
        """Read binary data from the Level_0 Cell_D file.

        Returns array of shape (ncomp, nz, ny, nx).
        """
        cell_d = self._path / "Level_0" / "Cell_D_00000"
        if not cell_d.exists():
            raise FileNotFoundError(f"Cell data file not found: {cell_d}")

        with open(cell_d, "rb") as f:
            # Read ASCII header line
            header_line = f.readline().decode("ascii")
            m = _FAB_HEADER_RE.match(header_line)
            if not m:
                raise ValueError(f"Cannot parse FAB header: {header_line!r}")

            byte_size = int(m.group(1))
            ncomp = int(m.group(8))
            nx = int(m.group(4)) - int(m.group(1)) + 1
            # Re-extract from groups properly
            lo_x, lo_y, lo_z = int(m.group(2)), int(m.group(3)), int(m.group(4))
            hi_x, hi_y, hi_z = int(m.group(5)), int(m.group(6)), int(m.group(7))
            nx = hi_x - lo_x + 1
            ny = hi_y - lo_y + 1
            nz = hi_z - lo_z + 1

            ncells = nx * ny * nz
            total_vals = ncells * ncomp

            if byte_size == 8:
                raw = f.read(total_vals * 8)
                data = np.frombuffer(raw, dtype=np.float64)
            else:
                raw = f.read(total_vals * 4)
                data = np.frombuffer(raw, dtype=np.float32)

        # Data is stored in Fortran order: x varies fastest, then y, then z,
        # one component at a time.
        return data.reshape((ncomp, nz, ny, nx))

    def _ensure_loaded(self) -> np.ndarray:
        """Load data if not cached. Returns (ncomp, nz, ny, nx) array."""
        if "_all" not in self._field_cache:
            self._field_cache["_all"] = self._read_fab_data()
        return self._field_cache["_all"]

    def get_variables(self) -> list[str]:
        return list(self._variables)

    def get_dimensions(self) -> dict[str, int]:
        return {"x": self._nx, "y": self._ny, "z": self._nz}

    def get_time_steps(self) -> list[float]:
        return [self._time]

    def get_coordinates(self) -> dict[str, np.ndarray]:
        """Compute cell-center coordinates from domain bounds and cell sizes."""
        x = np.linspace(
            self._prob_lo[0] + self._dx / 2,
            self._prob_hi[0] - self._dx / 2,
            self._nx,
        )
        y = np.linspace(
            self._prob_lo[1] + self._dy / 2,
            self._prob_hi[1] - self._dy / 2,
            self._ny,
        )
        z = np.linspace(
            self._prob_lo[2] + self._dz / 2,
            self._prob_hi[2] - self._dz / 2,
            self._nz,
        )
        return {"x": x, "y": y, "z": z}

    def get_field(self, variable: str, time_index: int = 0) -> np.ndarray:
        """Return the 3D field array (z, y, x) for a variable."""
        if variable not in self._variables:
            raise KeyError(f"Variable not found: {variable}")
        comp_idx = self._variables.index(variable)
        data = self._ensure_loaded()
        return data[comp_idx]  # shape (nz, ny, nx)

    def get_slice(
        self, variable: str, time_index: int, axis: str, index: int
    ) -> np.ndarray:
        """Return a 2D slice along an axis."""
        if axis not in ("x", "y", "z"):
            raise ValueError(f"Invalid axis: {axis!r}")
        field = self.get_field(variable, time_index)
        match axis:
            case "x":
                return field[:, :, index]
            case "y":
                return field[:, index, :]
            case "z":
                return field[index, :, :]

    def get_variable_info(self, variable: str) -> dict[str, Any]:
        if variable not in self._variables:
            raise KeyError(f"Variable not found: {variable}")
        return {
            "units": "",
            "long_name": variable,
            "shape": (self._nz, self._ny, self._nx),
            "dims": ["z", "y", "x"],
        }

    def get_statistics(self, variable: str, time_index: int = 0) -> dict[str, float]:
        field = self.get_field(variable, time_index)
        return {
            "min": float(np.nanmin(field)),
            "max": float(np.nanmax(field)),
            "mean": float(np.nanmean(field)),
        }

    def close(self) -> None:
        self._field_cache.clear()


# ---------------------------------------------------------------------------
# MultiAMReXReader — combines multiple plotfile directories as time series
# ---------------------------------------------------------------------------


class MultiAMReXReader:
    """Read multiple AMReX plotfile directories as a single time series.

    Scans a parent directory for plt* subdirectories and opens each one.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._readers: list[AMReXReader] = []
        self._times: list[float] = []

        # Find all plt* directories sorted by name
        plt_dirs = sorted(
            d for d in self._path.iterdir()
            if d.is_dir() and d.name.startswith("plt") and (d / "Header").exists()
            and not d.name.endswith(".old")
            and ".old." not in d.name
        )
        if not plt_dirs:
            raise ValueError(f"No AMReX plotfile directories found in {self._path}")

        for d in plt_dirs:
            reader = AMReXReader(d)
            self._readers.append(reader)
            self._times.append(reader.get_time_steps()[0])

        logger.info(
            "Opened %d AMReX plotfiles in %s (times: %s)",
            len(self._readers), self._path, self._times,
        )

    def get_variables(self) -> list[str]:
        return self._readers[0].get_variables()

    def get_dimensions(self) -> dict[str, int]:
        return self._readers[0].get_dimensions()

    def get_time_steps(self) -> list[float]:
        return list(self._times)

    def get_coordinates(self) -> dict[str, np.ndarray]:
        return self._readers[0].get_coordinates()

    def get_field(self, variable: str, time_index: int) -> np.ndarray:
        if time_index < 0 or time_index >= len(self._readers):
            raise IndexError(
                f"time_index {time_index} out of range [0, {len(self._readers)})"
            )
        return self._readers[time_index].get_field(variable)

    def get_slice(
        self, variable: str, time_index: int, axis: str, index: int
    ) -> np.ndarray:
        if time_index < 0 or time_index >= len(self._readers):
            raise IndexError(
                f"time_index {time_index} out of range [0, {len(self._readers)})"
            )
        return self._readers[time_index].get_slice(variable, 0, axis, index)

    def get_variable_info(self, variable: str) -> dict[str, Any]:
        return self._readers[0].get_variable_info(variable)

    def get_statistics(self, variable: str, time_index: int) -> dict[str, float]:
        return self._readers[time_index].get_statistics(variable)

    def close(self) -> None:
        for r in self._readers:
            r.close()


# ---------------------------------------------------------------------------
# Auto-detect and open
# ---------------------------------------------------------------------------


def open_output(path: str | Path) -> NetCDFReader | AMReXReader | MultiAMReXReader:
    """Open an output file or directory, auto-detecting the format.

    - If *path* is a file with .nc/.nc4/.cdf extension → NetCDFReader
    - If *path* is a directory containing a Header file → AMReXReader
    - If *path* is a directory containing plt* subdirs → MultiAMReXReader
    """
    p = Path(path)
    if p.is_file() and p.suffix in (".nc", ".nc4", ".cdf"):
        return NetCDFReader(p)
    if p.is_dir() and (p / "Header").exists():
        return AMReXReader(p)
    if p.is_dir():
        # Check for plt* subdirectories
        plt_dirs = [
            d for d in p.iterdir()
            if d.is_dir() and d.name.startswith("plt") and (d / "Header").exists()
        ]
        if plt_dirs:
            return MultiAMReXReader(p)
    raise ValueError(
        f"Cannot determine output format for {p}. "
        f"Expected a .nc file, an AMReX plotfile directory, "
        f"or a directory containing plt* subdirectories."
    )
