"""Tests for parameter sweep logic."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pytest

from remora_gui.core.sweep import (
    SweepAxis,
    SweepConfig,
    generate_sweep_combinations,
    generate_sweep_inputs,
)


class TestSweepAxis:
    """Test SweepAxis range and explicit value modes."""

    def test_range_values(self) -> None:
        axis = SweepAxis(key="remora.fixed_dt", start=100.0, end=500.0, step=100.0)
        vals = axis.values()
        assert vals == pytest.approx([100.0, 200.0, 300.0, 400.0, 500.0])

    def test_range_excludes_overshoot(self) -> None:
        axis = SweepAxis(key="remora.fixed_dt", start=100.0, end=350.0, step=100.0)
        vals = axis.values()
        assert vals == pytest.approx([100.0, 200.0, 300.0])

    def test_explicit_values(self) -> None:
        axis = SweepAxis(key="remora.Akv_bak", explicit=[1e-4, 1e-3, 1e-2])
        vals = axis.values()
        assert vals == [1e-4, 1e-3, 1e-2]

    def test_range_requires_start_end_step(self) -> None:
        axis = SweepAxis(key="x")
        with pytest.raises(ValueError, match=r"range.*or explicit"):
            axis.values()

    def test_explicit_takes_priority_over_range(self) -> None:
        axis = SweepAxis(
            key="x", start=0.0, end=10.0, step=1.0, explicit=[5, 10, 15]
        )
        assert axis.values() == [5, 10, 15]

    def test_single_value_range(self) -> None:
        axis = SweepAxis(key="x", start=5.0, end=5.0, step=1.0)
        assert axis.values() == [5.0]


class TestGenerateSweepCombinations:
    """Test combinatorial generation from multiple axes."""

    def test_single_axis(self) -> None:
        axes = [SweepAxis(key="dt", explicit=[100, 200, 300])]
        combos = generate_sweep_combinations(axes)
        assert len(combos) == 3
        assert combos[0] == {"dt": 100}
        assert combos[2] == {"dt": 300}

    def test_two_axes_cartesian_product(self) -> None:
        axes = [
            SweepAxis(key="dt", explicit=[100, 200]),
            SweepAxis(key="visc", explicit=[1e-3, 1e-4]),
        ]
        combos = generate_sweep_combinations(axes)
        assert len(combos) == 4
        assert {"dt": 100, "visc": 1e-3} in combos
        assert {"dt": 100, "visc": 1e-4} in combos
        assert {"dt": 200, "visc": 1e-3} in combos
        assert {"dt": 200, "visc": 1e-4} in combos

    def test_three_axes(self) -> None:
        axes = [
            SweepAxis(key="a", explicit=[1, 2]),
            SweepAxis(key="b", explicit=[3, 4]),
            SweepAxis(key="c", explicit=[5, 6]),
        ]
        combos = generate_sweep_combinations(axes)
        assert len(combos) == 8  # 2 * 2 * 2

    def test_empty_axes_returns_single_empty(self) -> None:
        combos = generate_sweep_combinations([])
        assert combos == [{}]


class TestGenerateSweepInputs:
    """Test input file generation for sweeps."""

    def test_generates_files(self, tmp_path: Path) -> None:
        base_params = OrderedDict(
            [("remora.fixed_dt", 300.0), ("remora.n_cell", [80, 80, 16])]
        )
        axes = [SweepAxis(key="remora.fixed_dt", explicit=[100.0, 200.0])]
        config = SweepConfig(
            base_params=base_params,
            axes=axes,
            name_template="sweep_dt{remora.fixed_dt}",
            output_dir=tmp_path,
        )
        results = generate_sweep_inputs(config)
        assert len(results) == 2
        for _name, path in results:
            assert path.exists()
            content = path.read_text()
            assert "remora.n_cell" in content

    def test_name_template_substitution(self, tmp_path: Path) -> None:
        base_params = OrderedDict([("dt", 0), ("visc", 0)])
        axes = [
            SweepAxis(key="dt", explicit=[100, 200]),
            SweepAxis(key="visc", explicit=[0.01]),
        ]
        config = SweepConfig(
            base_params=base_params,
            axes=axes,
            name_template="run_dt{dt}_v{visc}",
            output_dir=tmp_path,
        )
        results = generate_sweep_inputs(config)
        names = [name for name, _ in results]
        assert "run_dt100_v0.01" in names
        assert "run_dt200_v0.01" in names

    def test_default_name_template(self, tmp_path: Path) -> None:
        base_params = OrderedDict([("x", 0)])
        axes = [SweepAxis(key="x", explicit=[1, 2])]
        config = SweepConfig(
            base_params=base_params,
            axes=axes,
            output_dir=tmp_path,
        )
        results = generate_sweep_inputs(config)
        assert len(results) == 2
        # Default names should be sweep_000, sweep_001
        assert results[0][0] == "sweep_000"
        assert results[1][0] == "sweep_001"

    def test_overrides_base_params(self, tmp_path: Path) -> None:
        base_params = OrderedDict([("remora.fixed_dt", 300.0)])
        axes = [SweepAxis(key="remora.fixed_dt", explicit=[100.0])]
        config = SweepConfig(
            base_params=base_params, axes=axes, output_dir=tmp_path
        )
        results = generate_sweep_inputs(config)
        content = results[0][1].read_text()
        assert "100.0" in content
        assert "300.0" not in content
