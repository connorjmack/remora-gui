"""Remote execution engine — run REMORA on remote machines via SSH."""

from __future__ import annotations

import contextlib
import logging
import os
import re
import stat
import threading
import time
from collections.abc import Callable
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

import paramiko

from remora_gui.core.execution import parse_step
from remora_gui.core.settings import MachineProfile

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 30
_RECV_BUFSIZE = 4096


class RemoteExecutionEngine:
    """Run REMORA on a remote machine over SSH with live log streaming."""

    def __init__(
        self,
        profile: MachineProfile,
        input_file: str,
        num_procs: int = 1,
        *,
        max_step: int | None = None,
        on_stdout: Callable[[str], Any] | None = None,
        on_stderr: Callable[[str], Any] | None = None,
        on_finished: Callable[[int], Any] | None = None,
        on_progress: Callable[[int, int], Any] | None = None,
    ) -> None:
        self._profile = profile
        self._input_file = input_file
        self._num_procs = num_procs
        self._max_step = max_step

        self._on_stdout = on_stdout
        self._on_stderr = on_stderr
        self._on_finished = on_finished
        self._on_progress = on_progress

        self._client: paramiko.SSHClient | None = None
        self._channel: paramiko.Channel | None = None
        self._remote_pid: int | None = None
        self._exit_code: int | None = None
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def remote_input_path(self) -> str:
        """Return the full remote path where the input file will be placed."""
        wd = self._profile.working_directory
        if self._profile.os_type == "windows":
            return str(PureWindowsPath(wd) / self._input_file)
        return str(PurePosixPath(wd) / self._input_file)

    # ------------------------------------------------------------------
    # Command construction
    # ------------------------------------------------------------------

    def build_command(self) -> str:
        """Build the remote shell command string."""
        parts: list[str] = []

        # Pre-run commands
        for cmd in self._profile.pre_run_commands:
            parts.append(cmd)

        # cd to working directory
        wd = self._profile.working_directory
        if self._profile.os_type == "windows":
            parts.append(f"cd /d {wd}")
        else:
            parts.append(f"cd {wd}")

        # Execution command
        exe = self._profile.remora_executable_path
        if self._num_procs > 1:
            mpi = self._profile.mpi_command
            parts.append(f"{mpi} -np {self._num_procs} {exe} {self._input_file}")
        else:
            parts.append(f"{exe} {self._input_file}")

        return " && ".join(parts)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self, *, password: str | None = None) -> None:
        """Establish SSH connection to the remote machine."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs: dict[str, Any] = {
                "hostname": self._profile.hostname,
                "port": self._profile.port,
                "username": self._profile.username,
                "timeout": _CONNECT_TIMEOUT,
            }

            match self._profile.auth_method:
                case "key":
                    connect_kwargs["key_filename"] = self._profile.ssh_key_path
                case "password":
                    connect_kwargs["password"] = password
                case "agent":
                    connect_kwargs["allow_agent"] = True

            client.connect(**connect_kwargs)
            self._client = client
            logger.info("Connected to %s@%s", self._profile.username, self._profile.hostname)
        except (OSError, paramiko.SSHException) as exc:
            raise ConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("Disconnected from %s", self._profile.hostname)

    def is_connected(self) -> bool:
        """Return True if the SSH connection is active."""
        if self._client is None:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    def _require_connection(self) -> paramiko.SSHClient:
        """Raise ConnectionError if not connected, otherwise return the client."""
        if not self.is_connected() or self._client is None:
            raise ConnectionError("Not connected. Call connect() first.")
        return self._client

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def upload_input(
        self,
        local_path: str,
        remote_path: str | None = None,
    ) -> None:
        """Upload an input file to the remote working directory via SFTP."""
        client = self._require_connection()
        if remote_path is None:
            remote_path = self.remote_input_path()

        sftp = client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
            logger.info("Uploaded %s -> %s", local_path, remote_path)
        finally:
            sftp.close()

    def download_output(
        self,
        remote_dir: str,
        local_dir: str,
        *,
        progress_callback: Callable[[str, int, int], Any] | None = None,
    ) -> None:
        """Download output files from a remote directory via SFTP."""
        client = self._require_connection()
        sftp = client.open_sftp()
        try:
            os.makedirs(local_dir, exist_ok=True)
            entries = sftp.listdir_attr(remote_dir)
            files = [e for e in entries if stat.S_ISREG(e.st_mode or 0)]

            for i, entry in enumerate(files):
                remote_file = f"{remote_dir}/{entry.filename}"
                local_file = os.path.join(local_dir, entry.filename)
                sftp.get(remote_file, local_file)
                if progress_callback:
                    progress_callback(entry.filename, i + 1, len(files))
                logger.info("Downloaded %s", entry.filename)
        finally:
            sftp.close()

    # ------------------------------------------------------------------
    # Execution lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Execute REMORA on the remote machine and stream output."""
        client = self._require_connection()
        transport = client.get_transport()
        if transport is None:
            raise ConnectionError("SSH transport unavailable")

        if self._channel is not None and not self._channel.exit_status_ready():
            raise RuntimeError("Remote process already running")

        self._exit_code = None
        channel = transport.open_session()
        self._channel = channel

        cmd = self.build_command()
        logger.info("Executing: %s", cmd)
        channel.exec_command(cmd)

        # Start reader thread
        reader = threading.Thread(target=self._read_channel, daemon=True)
        reader.start()
        self._threads = [reader]

    def stop(self) -> None:
        """Kill the remote process."""
        if self._client is None:
            return

        # Try to kill by PID if we have one
        if self._remote_pid is not None:
            try:
                self._client.exec_command(f"kill -TERM {self._remote_pid}")
                time.sleep(2)
                self._client.exec_command(f"kill -9 {self._remote_pid}")
            except Exception:
                logger.warning("Failed to kill remote process %s", self._remote_pid)

        # Close the channel
        if self._channel is not None:
            with contextlib.suppress(Exception):
                self._channel.close()

    def is_running(self) -> bool:
        if self._channel is None:
            return False
        return not self._channel.exit_status_ready()

    def exit_code(self) -> int | None:
        return self._exit_code

    # ------------------------------------------------------------------
    # Channel reader
    # ------------------------------------------------------------------

    _PID_RE = re.compile(r"PID:\s*(\d+)")

    def _read_channel(self) -> None:
        """Read stdout/stderr from the SSH channel until it closes."""
        assert self._channel is not None
        stdout_buf = ""
        stderr_buf = ""

        while not self._channel.exit_status_ready():
            if self._channel.recv_ready():
                data = self._channel.recv(_RECV_BUFSIZE).decode("utf-8", errors="replace")
                stdout_buf += data
                while "\n" in stdout_buf:
                    line, stdout_buf = stdout_buf.split("\n", 1)
                    self._handle_stdout_line(line)

            if self._channel.recv_stderr_ready():
                data = self._channel.recv_stderr(_RECV_BUFSIZE).decode(
                    "utf-8", errors="replace"
                )
                stderr_buf += data
                while "\n" in stderr_buf:
                    line, stderr_buf = stderr_buf.split("\n", 1)
                    if self._on_stderr:
                        self._on_stderr(line)

            time.sleep(0.05)

        # Drain remaining data
        while self._channel.recv_ready():
            data = self._channel.recv(_RECV_BUFSIZE).decode("utf-8", errors="replace")
            stdout_buf += data
        while "\n" in stdout_buf:
            line, stdout_buf = stdout_buf.split("\n", 1)
            self._handle_stdout_line(line)
        if stdout_buf.strip():
            self._handle_stdout_line(stdout_buf)

        while self._channel.recv_stderr_ready():
            data = self._channel.recv_stderr(_RECV_BUFSIZE).decode(
                "utf-8", errors="replace"
            )
            stderr_buf += data
        while "\n" in stderr_buf:
            line, stderr_buf = stderr_buf.split("\n", 1)
            if self._on_stderr:
                self._on_stderr(line)
        if stderr_buf.strip() and self._on_stderr:
            self._on_stderr(stderr_buf)

        self._exit_code = self._channel.recv_exit_status()
        if self._on_finished:
            self._on_finished(self._exit_code)

    def _handle_stdout_line(self, line: str) -> None:
        """Process a single stdout line — emit callback and parse progress."""
        if self._on_stdout:
            self._on_stdout(line)

        # Try to pick up the PID from output
        pid_match = self._PID_RE.search(line)
        if pid_match:
            self._remote_pid = int(pid_match.group(1))

        # Parse progress
        step = parse_step(line)
        if step is not None and self._on_progress and self._max_step:
            self._on_progress(step, self._max_step)
