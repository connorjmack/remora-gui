"""Tests for core/execution.py — Task 1.8."""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

from remora_gui.core.execution import LocalExecutionEngine, parse_step

# ---------------------------------------------------------------------------
# parse_step
# ---------------------------------------------------------------------------


class TestParseStep:
    def test_extracts_step_number(self) -> None:
        assert parse_step("Step 42") == 42

    def test_step_in_longer_line(self) -> None:
        assert parse_step("REMORA: Step 100 completed") == 100

    def test_no_match_returns_none(self) -> None:
        assert parse_step("some other output") is None

    def test_step_zero(self) -> None:
        assert parse_step("Step 0") == 0

    def test_large_step(self) -> None:
        assert parse_step("Step 999999") == 999999


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_single_proc_no_mpi(self) -> None:
        engine = LocalExecutionEngine(
            executable="/usr/bin/remora",
            input_file="inputs",
            working_dir="/tmp/run",
            num_procs=1,
        )
        cmd = engine.build_command()
        assert cmd == ["/usr/bin/remora", "inputs"]

    def test_multi_proc_with_mpi(self) -> None:
        engine = LocalExecutionEngine(
            executable="/usr/bin/remora",
            input_file="inputs",
            working_dir="/tmp/run",
            mpi_command="mpirun",
            num_procs=4,
        )
        cmd = engine.build_command()
        assert cmd == ["mpirun", "-np", "4", "/usr/bin/remora", "inputs"]

    def test_custom_mpi_command(self) -> None:
        engine = LocalExecutionEngine(
            executable="/opt/remora",
            input_file="my_inputs",
            working_dir="/work",
            mpi_command="srun",
            num_procs=8,
        )
        cmd = engine.build_command()
        assert cmd[0] == "srun"
        assert "-np" in cmd
        assert "8" in cmd


# ---------------------------------------------------------------------------
# stop() sends SIGTERM
# ---------------------------------------------------------------------------


class TestStop:
    @patch("remora_gui.core.execution.subprocess.Popen")
    def test_stop_sends_sigterm(self, mock_popen_cls: MagicMock) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # process is running
        mock_proc.wait.return_value = 0
        mock_popen_cls.return_value = mock_proc

        engine = LocalExecutionEngine(
            executable="remora",
            input_file="inputs",
            working_dir="/tmp",
        )
        # Manually set process to our mock (skip start's threading)
        engine._process = mock_proc

        engine.stop()
        mock_proc.send_signal.assert_called_once_with(signal.SIGTERM)

    def test_stop_noop_when_not_started(self) -> None:
        engine = LocalExecutionEngine(
            executable="remora",
            input_file="inputs",
            working_dir="/tmp",
        )
        # Should not raise
        engine.stop()


# ---------------------------------------------------------------------------
# is_running / exit_code
# ---------------------------------------------------------------------------


class TestState:
    def test_not_running_before_start(self) -> None:
        engine = LocalExecutionEngine(
            executable="remora",
            input_file="inputs",
            working_dir="/tmp",
        )
        assert engine.is_running() is False
        assert engine.exit_code() is None
