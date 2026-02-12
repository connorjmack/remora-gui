"""Tests for core/settings.py — Task 1.7."""

from __future__ import annotations

from pathlib import Path

from remora_gui.core.settings import AppSettings, MachineProfile

# ---------------------------------------------------------------------------
# MachineProfile round-trip
# ---------------------------------------------------------------------------


class TestMachineProfile:
    def test_to_dict_from_dict_round_trip(self) -> None:
        profile = MachineProfile(
            id="abc123",
            name="GPU Box",
            host_type="remote",
            hostname="192.168.1.50",
            port=22,
            username="connor",
            auth_method="key",
            ssh_key_path="~/.ssh/id_rsa",
            os_type="windows",
            remora_executable_path="C:\\REMORA\\bin\\remora.exe",
            mpi_command="mpiexec",
            default_num_procs=4,
            working_directory="C:\\runs",
            gpu_enabled=True,
            num_gpus=1,
            gpu_type="NVIDIA RTX 4090",
            pre_run_commands=["module load cuda"],
        )
        d = profile.to_dict()
        restored = MachineProfile.from_dict(d)

        assert restored.id == profile.id
        assert restored.name == profile.name
        assert restored.host_type == profile.host_type
        assert restored.hostname == profile.hostname
        assert restored.port == profile.port
        assert restored.username == profile.username
        assert restored.auth_method == profile.auth_method
        assert restored.ssh_key_path == profile.ssh_key_path
        assert restored.os_type == profile.os_type
        assert restored.remora_executable_path == profile.remora_executable_path
        assert restored.mpi_command == profile.mpi_command
        assert restored.default_num_procs == profile.default_num_procs
        assert restored.working_directory == profile.working_directory
        assert restored.gpu_enabled == profile.gpu_enabled
        assert restored.num_gpus == profile.num_gpus
        assert restored.gpu_type == profile.gpu_type
        assert restored.pre_run_commands == profile.pre_run_commands

    def test_local_profile_minimal(self) -> None:
        profile = MachineProfile(
            id="local1",
            name="Local Mac",
            host_type="local",
            os_type="macos",
            remora_executable_path="/usr/local/bin/remora",
            working_directory="~/runs",
        )
        d = profile.to_dict()
        restored = MachineProfile.from_dict(d)
        assert restored.hostname is None
        assert restored.username is None
        assert restored.gpu_enabled is False


# ---------------------------------------------------------------------------
# AppSettings CRUD
# ---------------------------------------------------------------------------


def _make_profile(name: str = "Test", host_type: str = "local") -> MachineProfile:
    import uuid

    return MachineProfile(
        id=uuid.uuid4().hex,
        name=name,
        host_type=host_type,  # type: ignore[arg-type]
        os_type="linux",
        remora_executable_path="/usr/bin/remora",
        working_directory="/tmp/runs",
    )


class TestAppSettings:
    def test_empty_on_fresh_dir(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        assert settings.get_machine_profiles() == []
        assert settings.get_recent_projects() == []

    def test_save_and_get_machine_profile(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        p = _make_profile("Box A")
        settings.save_machine_profile(p)

        profiles = settings.get_machine_profiles()
        assert len(profiles) == 1
        assert profiles[0].name == "Box A"

    def test_update_existing_profile(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        p = _make_profile("Original")
        settings.save_machine_profile(p)

        p.name = "Updated"
        settings.save_machine_profile(p)

        profiles = settings.get_machine_profiles()
        assert len(profiles) == 1
        assert profiles[0].name == "Updated"

    def test_delete_machine_profile(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        p = _make_profile("ToDelete")
        settings.save_machine_profile(p)
        settings.delete_machine_profile(p.id)

        assert settings.get_machine_profiles() == []

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        s1 = AppSettings(config_dir)
        s1.save_machine_profile(_make_profile("Persistent"))

        s2 = AppSettings(config_dir)
        assert len(s2.get_machine_profiles()) == 1
        assert s2.get_machine_profiles()[0].name == "Persistent"

    def test_default_project_dir(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        # Default fallback
        assert settings.get_default_project_dir() == Path.home() / "remora_projects"

        settings.set_default_project_dir("/custom/path")
        assert settings.get_default_project_dir() == Path("/custom/path")

    def test_recent_projects(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        settings.add_recent_project("/proj/a")
        settings.add_recent_project("/proj/b")
        settings.add_recent_project("/proj/c")

        recents = settings.get_recent_projects()
        assert recents == ["/proj/c", "/proj/b", "/proj/a"]

    def test_recent_projects_deduplicates(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        settings.add_recent_project("/proj/a")
        settings.add_recent_project("/proj/b")
        settings.add_recent_project("/proj/a")  # move to front

        recents = settings.get_recent_projects()
        assert recents == ["/proj/a", "/proj/b"]

    def test_recent_projects_max_limit(self, tmp_path: Path) -> None:
        settings = AppSettings(tmp_path / "config")
        for i in range(15):
            settings.add_recent_project(f"/proj/{i}")

        assert len(settings.get_recent_projects()) == 10
