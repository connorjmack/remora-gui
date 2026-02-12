"""Tests for core/remote.py — Task 3.1."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from remora_gui.core.remote import RemoteExecutionEngine
from remora_gui.core.settings import MachineProfile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(**overrides: object) -> MachineProfile:
    defaults = {
        "id": "test-machine",
        "name": "Test Machine",
        "host_type": "remote",
        "hostname": "gpu-box.local",
        "port": 22,
        "username": "researcher",
        "auth_method": "key",
        "ssh_key_path": "/home/user/.ssh/id_rsa",
        "os_type": "linux",
        "remora_executable_path": "/opt/remora/bin/remora",
        "mpi_command": "mpirun",
        "default_num_procs": 4,
        "working_directory": "/scratch/runs",
        "pre_run_commands": [],
    }
    defaults.update(overrides)
    return MachineProfile(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestBuildRemoteCommand:
    def test_linux_single_proc(self) -> None:
        profile = _make_profile(default_num_procs=1)
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        cmd = engine.build_command()
        assert cmd == "cd /scratch/runs && /opt/remora/bin/remora inputs"

    def test_linux_multi_proc(self) -> None:
        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=4,
        )
        cmd = engine.build_command()
        assert cmd == "cd /scratch/runs && mpirun -np 4 /opt/remora/bin/remora inputs"

    def test_custom_mpi_command(self) -> None:
        profile = _make_profile(mpi_command="srun")
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=8,
        )
        cmd = engine.build_command()
        assert "srun -np 8" in cmd

    def test_pre_run_commands(self) -> None:
        profile = _make_profile(
            pre_run_commands=["module load cuda/11.8", "export OMP_NUM_THREADS=4"]
        )
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=2,
        )
        cmd = engine.build_command()
        assert cmd.startswith("module load cuda/11.8 && export OMP_NUM_THREADS=4 && ")

    def test_windows_path_handling(self) -> None:
        profile = _make_profile(
            os_type="windows",
            remora_executable_path="C:\\REMORA\\bin\\remora.exe",
            working_directory="C:\\scratch\\runs",
        )
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        cmd = engine.build_command()
        # Windows uses 'cd /d' for cross-drive support
        assert "cd /d C:\\scratch\\runs" in cmd
        assert "C:\\REMORA\\bin\\remora.exe inputs" in cmd


# ---------------------------------------------------------------------------
# SSH connection
# ---------------------------------------------------------------------------


class TestConnect:
    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_connect_with_key(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile(auth_method="key", ssh_key_path="/home/user/.ssh/id_rsa")
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()

        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname="gpu-box.local",
            port=22,
            username="researcher",
            key_filename="/home/user/.ssh/id_rsa",
            timeout=30,
        )

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_connect_with_password(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile(auth_method="password")
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect(password="secret123")

        mock_client.connect.assert_called_once_with(
            hostname="gpu-box.local",
            port=22,
            username="researcher",
            password="secret123",
            timeout=30,
        )

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_connect_with_agent(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile(auth_method="agent")
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()

        mock_client.connect.assert_called_once_with(
            hostname="gpu-box.local",
            port=22,
            username="researcher",
            allow_agent=True,
            timeout=30,
        )

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_connect_failure_raises(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.connect.side_effect = OSError("Connection refused")
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        with pytest.raises(ConnectionError, match="Connection refused"):
            engine.connect()

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_disconnect(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()
        engine.disconnect()
        mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# File transfer
# ---------------------------------------------------------------------------


class TestFileTransfer:
    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_upload_input(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()
        engine.upload_input("/local/path/inputs")

        mock_sftp.put.assert_called_once_with(
            "/local/path/inputs",
            "/scratch/runs/inputs",
        )
        mock_sftp.close.assert_called_once()

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_upload_custom_remote_path(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()
        engine.upload_input("/local/path/inputs", remote_path="/custom/dir/my_inputs")

        mock_sftp.put.assert_called_once_with(
            "/local/path/inputs",
            "/custom/dir/my_inputs",
        )

    @patch("remora_gui.core.remote.os.makedirs")
    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_download_output(self, mock_ssh_cls: MagicMock, mock_makedirs: MagicMock) -> None:
        mock_client = MagicMock()
        mock_sftp = MagicMock()
        mock_client.open_sftp.return_value = mock_sftp
        # Simulate a remote directory with files
        mock_attr1 = MagicMock()
        mock_attr1.filename = "output_0001.nc"
        mock_attr1.st_mode = 0o100644  # regular file
        mock_attr2 = MagicMock()
        mock_attr2.filename = "output_0002.nc"
        mock_attr2.st_mode = 0o100644
        mock_sftp.listdir_attr.return_value = [mock_attr1, mock_attr2]
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()

        progress_cb = MagicMock()
        engine.download_output(
            remote_dir="/scratch/runs/output",
            local_dir="/local/output",
            progress_callback=progress_cb,
        )

        mock_makedirs.assert_called_once_with("/local/output", exist_ok=True)
        assert mock_sftp.get.call_count == 2
        assert progress_cb.call_count == 2

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_upload_requires_connection(self, mock_ssh_cls: MagicMock) -> None:
        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        with pytest.raises(ConnectionError, match="Not connected"):
            engine.upload_input("/local/path/inputs")


# ---------------------------------------------------------------------------
# Remote execution
# ---------------------------------------------------------------------------


class TestRemoteExecution:
    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_start_executes_command(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()
        # Main loop: one recv, then exit
        mock_channel.recv_ready.side_effect = [True, False, False, False]
        mock_channel.recv.return_value = b"Step 1\n"
        mock_channel.recv_stderr_ready.side_effect = [False, False, False]
        mock_channel.exit_status_ready.side_effect = [False, True]
        mock_channel.recv_exit_status.return_value = 0
        mock_transport.open_session.return_value = mock_channel
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client

        on_stdout = MagicMock()
        on_finished = MagicMock()

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=4,
            on_stdout=on_stdout,
            on_finished=on_finished,
        )
        engine.connect()
        engine.start()

        # Wait for reader thread to finish
        for t in engine._threads:
            t.join(timeout=5)

        mock_channel.exec_command.assert_called_once()
        cmd_arg = mock_channel.exec_command.call_args[0][0]
        assert "mpirun -np 4" in cmd_arg
        assert "/opt/remora/bin/remora inputs" in cmd_arg

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_stop_sends_kill(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_channel = MagicMock()
        mock_channel.exit_status_ready.return_value = False
        mock_transport.open_session.return_value = mock_channel
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        engine.connect()
        # Simulate a running channel
        engine._channel = mock_channel
        engine._remote_pid = 12345

        engine.stop()

        # Should execute kill command over SSH
        mock_client.exec_command.assert_called()
        kill_cmd = mock_client.exec_command.call_args[0][0]
        assert "kill" in kill_cmd
        assert "12345" in kill_cmd

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_start_requires_connection(self, mock_ssh_cls: MagicMock) -> None:
        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        with pytest.raises(ConnectionError, match="Not connected"):
            engine.start()


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestRemoteState:
    def test_not_running_before_start(self) -> None:
        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        assert engine.is_running() is False
        assert engine.exit_code() is None

    @patch("remora_gui.core.remote.paramiko.SSHClient")
    def test_is_connected(self, mock_ssh_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client

        profile = _make_profile()
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        assert engine.is_connected() is False
        engine.connect()
        assert engine.is_connected() is True


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------


class TestPathHandling:
    def test_remote_input_path_linux(self) -> None:
        profile = _make_profile(os_type="linux", working_directory="/scratch/runs")
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        assert engine.remote_input_path() == "/scratch/runs/inputs"

    def test_remote_input_path_windows(self) -> None:
        profile = _make_profile(
            os_type="windows",
            working_directory="C:\\scratch\\runs",
        )
        engine = RemoteExecutionEngine(
            profile=profile,
            input_file="inputs",
            num_procs=1,
        )
        assert engine.remote_input_path() == "C:\\scratch\\runs\\inputs"
