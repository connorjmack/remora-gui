"""Tests for import/export enhancements — Task 4.4."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from remora_gui.core.export import (
    export_json,
    export_shell_script,
    import_json,
)
from remora_gui.core.input_file import parse_input_string


class TestExportJSON:
    """Test JSON export/import round-trip."""

    def test_export_produces_valid_json(self, tmp_path: Path) -> None:
        params = OrderedDict([("remora.fixed_dt", 300.0), ("remora.n_cell", [80, 80, 16])])
        path = tmp_path / "config.json"
        export_json(params, path)
        data = json.loads(path.read_text())
        assert data["remora.fixed_dt"] == 300.0
        assert data["remora.n_cell"] == [80, 80, 16]

    def test_round_trip_through_json(self, tmp_path: Path) -> None:
        params = OrderedDict([
            ("remora.fixed_dt", 300.0),
            ("remora.use_coriolis", True),
            ("remora.n_cell", [41, 80, 16]),
            ("remora.bc.xlo.type", "SlipWall"),
        ])
        path = tmp_path / "config.json"
        export_json(params, path)
        restored = import_json(path)
        assert restored == params

    def test_preserves_ordering(self, tmp_path: Path) -> None:
        params = OrderedDict([("b.key", 1), ("a.key", 2), ("c.key", 3)])
        path = tmp_path / "config.json"
        export_json(params, path)
        restored = import_json(path)
        assert list(restored.keys()) == ["b.key", "a.key", "c.key"]

    def test_handles_empty_params(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        export_json({}, path)
        restored = import_json(path)
        assert restored == {}


class TestExportShellScript:
    """Test shell script export."""

    def test_produces_executable_script(self, tmp_path: Path) -> None:
        params = OrderedDict([
            ("remora.fixed_dt", 300.0),
            ("remora.use_coriolis", True),
        ])
        path = tmp_path / "run.sh"
        export_shell_script(
            params, path, executable="/path/to/REMORA", num_procs=4
        )
        content = path.read_text()
        assert content.startswith("#!/bin/bash")
        assert "mpirun" in content or "mpiexec" in content
        assert "-n 4" in content
        assert "remora.fixed_dt=300.0" in content
        assert "remora.use_coriolis=true" in content

    def test_single_proc_no_mpi(self, tmp_path: Path) -> None:
        params = OrderedDict([("remora.v", 0)])
        path = tmp_path / "run.sh"
        export_shell_script(params, path, executable="./REMORA", num_procs=1)
        content = path.read_text()
        assert "mpirun" not in content
        assert "./REMORA" in content

    def test_includes_input_file_arg(self, tmp_path: Path) -> None:
        params = OrderedDict([("remora.v", 0)])
        path = tmp_path / "run.sh"
        export_shell_script(
            params, path, executable="./REMORA", input_file="inputs"
        )
        content = path.read_text()
        assert "inputs" in content

    def test_bool_formatting(self, tmp_path: Path) -> None:
        params = OrderedDict([("remora.flag", False)])
        path = tmp_path / "run.sh"
        export_shell_script(params, path, executable="./REMORA")
        content = path.read_text()
        assert "remora.flag=false" in content

    def test_vector_formatting(self, tmp_path: Path) -> None:
        params = OrderedDict([("remora.n_cell", [41, 80, 16])])
        path = tmp_path / "run.sh"
        export_shell_script(params, path, executable="./REMORA")
        content = path.read_text()
        # Vectors should be quoted for shell: "41 80 16"
        assert '"41 80 16"' in content


class TestImportFromInputFile:
    """Test importing existing REMORA input files preserves unknown params."""

    def test_unknown_params_preserved(self) -> None:
        text = "remora.max_step = 10\ncustom.fancy_param = 42\n"
        result = parse_input_string(text)
        assert result["custom.fancy_param"] == 42
        assert result["remora.max_step"] == 10
