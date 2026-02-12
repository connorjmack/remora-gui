"""Tests for core/output_reader.py — Task 3.2."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from remora_gui.core.output_reader import (
    AMReXReader,
    NetCDFReader,
    open_output,
)

# ---------------------------------------------------------------------------
# Fixture: create a small synthetic NetCDF file
# ---------------------------------------------------------------------------


@pytest.fixture()
def netcdf_file(tmp_path: Path) -> Path:
    """Create a minimal NetCDF file mimicking REMORA output."""
    nx, ny, nz, nt = 10, 8, 5, 3
    x = np.linspace(0, 100, nx)
    y = np.linspace(0, 80, ny)
    z = np.linspace(-50, 0, nz)
    time = np.array([0.0, 300.0, 600.0])

    temp = np.random.default_rng(42).uniform(10, 25, (nt, nz, ny, nx))
    salt = np.random.default_rng(99).uniform(30, 36, (nt, nz, ny, nx))

    ds = xr.Dataset(
        {
            "temp": (["time", "z", "y", "x"], temp, {"units": "degC", "long_name": "Temperature"}),
            "salt": (["time", "z", "y", "x"], salt, {"units": "PSU", "long_name": "Salinity"}),
        },
        coords={
            "x": ("x", x, {"units": "m"}),
            "y": ("y", y, {"units": "m"}),
            "z": ("z", z, {"units": "m"}),
            "time": ("time", time, {"units": "s"}),
        },
    )
    path = tmp_path / "output.nc"
    ds.to_netcdf(path)
    return path


@pytest.fixture()
def amrex_dir(tmp_path: Path) -> Path:
    """Create a minimal AMReX plotfile directory structure."""
    plt_dir = tmp_path / "plt00100"
    plt_dir.mkdir()

    # Write Header file
    header = plt_dir / "Header"
    header.write_text(
        "HyperCLaw-V1.1\n"
        "2\n"
        "temp\n"
        "salt\n"
        "3\n"
        "600.0\n"
        "1\n"
        "0 0 0\n"
        "0 0 0 9 7 4\n"
        "0 0\n"
        "100.0 80.0 50.0\n"
        "0.0 0.0 0.0\n"
        "((0,0) (9,7,4) (0,0,0))\n"
        "Level_0/Cell\n"
    )
    return plt_dir


# ---------------------------------------------------------------------------
# NetCDFReader
# ---------------------------------------------------------------------------


class TestNetCDFReader:
    def test_open(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        assert reader is not None

    def test_get_variables(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        variables = reader.get_variables()
        assert "temp" in variables
        assert "salt" in variables
        assert len(variables) == 2

    def test_get_dimensions(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        dims = reader.get_dimensions()
        assert dims["x"] == 10
        assert dims["y"] == 8
        assert dims["z"] == 5
        assert dims["time"] == 3

    def test_get_time_steps(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        times = reader.get_time_steps()
        assert len(times) == 3
        assert times[0] == pytest.approx(0.0)
        assert times[1] == pytest.approx(300.0)
        assert times[2] == pytest.approx(600.0)

    def test_get_coordinates(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        coords = reader.get_coordinates()
        assert "x" in coords
        assert "y" in coords
        assert "z" in coords
        assert len(coords["x"]) == 10
        assert coords["z"][0] == pytest.approx(-50.0)

    def test_get_field(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        field = reader.get_field("temp", time_index=0)
        assert field.shape == (5, 8, 10)  # z, y, x
        assert field.dtype == np.float64

    def test_get_field_last_time(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        field = reader.get_field("temp", time_index=2)
        assert field.shape == (5, 8, 10)

    def test_get_field_invalid_variable(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        with pytest.raises(KeyError, match="velocity"):
            reader.get_field("velocity", time_index=0)

    def test_get_field_invalid_time_index(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        with pytest.raises(IndexError):
            reader.get_field("temp", time_index=99)

    def test_get_slice_x(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        slc = reader.get_slice("temp", time_index=0, axis="x", index=5)
        assert slc.shape == (5, 8)  # z, y

    def test_get_slice_y(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        slc = reader.get_slice("temp", time_index=0, axis="y", index=3)
        assert slc.shape == (5, 10)  # z, x

    def test_get_slice_z(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        slc = reader.get_slice("temp", time_index=0, axis="z", index=2)
        assert slc.shape == (8, 10)  # y, x

    def test_get_slice_invalid_axis(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        with pytest.raises(ValueError, match="axis"):
            reader.get_slice("temp", time_index=0, axis="w", index=0)

    def test_get_variable_info(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        info = reader.get_variable_info("temp")
        assert info["units"] == "degC"
        assert info["long_name"] == "Temperature"
        assert "shape" in info

    def test_get_statistics(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        stats = reader.get_statistics("temp", time_index=0)
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert stats["min"] < stats["max"]

    def test_close(self, netcdf_file: Path) -> None:
        reader = NetCDFReader(netcdf_file)
        reader.close()
        # Should be safe to call twice
        reader.close()


# ---------------------------------------------------------------------------
# AMReXReader — header parsing only (no binary reads)
# ---------------------------------------------------------------------------


class TestAMReXReader:
    def test_open(self, amrex_dir: Path) -> None:
        reader = AMReXReader(amrex_dir)
        assert reader is not None

    def test_get_variables(self, amrex_dir: Path) -> None:
        reader = AMReXReader(amrex_dir)
        variables = reader.get_variables()
        assert "temp" in variables
        assert "salt" in variables

    def test_get_dimensions(self, amrex_dir: Path) -> None:
        reader = AMReXReader(amrex_dir)
        dims = reader.get_dimensions()
        assert "ndim" in dims

    def test_get_time(self, amrex_dir: Path) -> None:
        reader = AMReXReader(amrex_dir)
        times = reader.get_time_steps()
        assert len(times) == 1
        assert times[0] == pytest.approx(600.0)

    def test_missing_header_raises(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty_plt"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Header"):
            AMReXReader(empty_dir)


# ---------------------------------------------------------------------------
# open_output auto-detection
# ---------------------------------------------------------------------------


class TestOpenOutput:
    def test_detect_netcdf(self, netcdf_file: Path) -> None:
        reader = open_output(netcdf_file)
        assert isinstance(reader, NetCDFReader)

    def test_detect_amrex(self, amrex_dir: Path) -> None:
        reader = open_output(amrex_dir)
        assert isinstance(reader, AMReXReader)

    def test_unknown_raises(self, tmp_path: Path) -> None:
        unknown = tmp_path / "random.txt"
        unknown.write_text("hello")
        with pytest.raises(ValueError, match="Cannot determine"):
            open_output(unknown)
