"""Local execution engine for running REMORA as a subprocess."""

from __future__ import annotations

import re
import signal
import subprocess
import threading
from collections.abc import Callable
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Callback signatures
# ---------------------------------------------------------------------------


class ExecutionCallbacks(Protocol):
    """Callback interface for execution events."""

    def on_stdout(self, line: str) -> None: ...
    def on_stderr(self, line: str) -> None: ...
    def on_finished(self, exit_code: int) -> None: ...
    def on_progress(self, step: int, max_step: int) -> None: ...


# ---------------------------------------------------------------------------
# ExecutionEngine protocol
# ---------------------------------------------------------------------------


class ExecutionEngine(Protocol):
    """Common interface shared by local and remote engines."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...
    def exit_code(self) -> int | None: ...


# ---------------------------------------------------------------------------
# Progress parsing
# ---------------------------------------------------------------------------

_STEP_RE = re.compile(r"Step\s+(\d+)")


def parse_step(line: str) -> int | None:
    """Extract the step number from a REMORA stdout line, if present."""
    m = _STEP_RE.search(line)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# LocalExecutionEngine
# ---------------------------------------------------------------------------


class LocalExecutionEngine:
    """Run REMORA as a local subprocess with live log streaming."""

    def __init__(
        self,
        executable: str,
        input_file: str,
        working_dir: str,
        *,
        mpi_command: str = "mpirun",
        num_procs: int = 1,
        max_step: int | None = None,
        on_stdout: Callable[[str], Any] | None = None,
        on_stderr: Callable[[str], Any] | None = None,
        on_finished: Callable[[int], Any] | None = None,
        on_progress: Callable[[int, int], Any] | None = None,
    ) -> None:
        self._executable = executable
        self._input_file = input_file
        self._working_dir = working_dir
        self._mpi_command = mpi_command
        self._num_procs = num_procs
        self._max_step = max_step

        self._on_stdout = on_stdout
        self._on_stderr = on_stderr
        self._on_finished = on_finished
        self._on_progress = on_progress

        self._process: subprocess.Popen[str] | None = None
        self._exit_code: int | None = None
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Command building
    # ------------------------------------------------------------------

    def build_command(self) -> list[str]:
        """Return the command list that ``start()`` would invoke."""
        if self._num_procs > 1:
            return [
                self._mpi_command, "-np", str(self._num_procs),
                self._executable, self._input_file,
            ]
        return [self._executable, self._input_file]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn the REMORA subprocess and begin streaming output."""
        if self._process is not None and self._process.poll() is None:
            raise RuntimeError("Process already running")

        cmd = self.build_command()
        self._exit_code = None
        self._process = subprocess.Popen(
            cmd,
            cwd=self._working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Reader threads for stdout / stderr
        self._threads = [
            threading.Thread(target=self._read_stdout, daemon=True),
            threading.Thread(target=self._read_stderr, daemon=True),
        ]
        for t in self._threads:
            t.start()

        # Waiter thread to detect completion
        waiter = threading.Thread(target=self._wait, daemon=True)
        waiter.start()
        self._threads.append(waiter)

    def stop(self) -> None:
        """Send SIGTERM; if still running after 10 s, send SIGKILL."""
        if self._process is None or self._process.poll() is not None:
            return
        self._process.send_signal(signal.SIGTERM)
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()

    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def exit_code(self) -> int | None:
        return self._exit_code

    # ------------------------------------------------------------------
    # Internal reader / waiter threads
    # ------------------------------------------------------------------

    def _read_stdout(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        for line in self._process.stdout:
            text = line.rstrip("\n")
            if self._on_stdout:
                self._on_stdout(text)
            step = parse_step(text)
            if step is not None and self._on_progress and self._max_step:
                self._on_progress(step, self._max_step)

    def _read_stderr(self) -> None:
        assert self._process is not None and self._process.stderr is not None
        for line in self._process.stderr:
            text = line.rstrip("\n")
            if self._on_stderr:
                self._on_stderr(text)

    def _wait(self) -> None:
        assert self._process is not None
        self._process.wait()
        self._exit_code = self._process.returncode
        if self._on_finished:
            self._on_finished(self._exit_code)
