"""Machine profiles and application settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# ---------------------------------------------------------------------------
# MachineProfile
# ---------------------------------------------------------------------------


@dataclass
class MachineProfile:
    """Defines a target execution environment for REMORA."""

    id: str
    name: str
    host_type: Literal["local", "remote"]

    # Remote-only
    hostname: str | None = None
    port: int = 22
    username: str | None = None
    auth_method: Literal["key", "password", "agent"] = "key"
    ssh_key_path: str | None = None

    # Execution environment
    os_type: Literal["linux", "macos", "windows"] = "linux"
    remora_executable_path: str = ""
    mpi_command: str = "mpirun"
    default_num_procs: int = 1
    working_directory: str = ""

    # GPU
    gpu_enabled: bool = False
    num_gpus: int = 0
    gpu_type: str = ""

    # Pre-run
    pre_run_commands: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "host_type": self.host_type,
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "auth_method": self.auth_method,
            "ssh_key_path": self.ssh_key_path,
            "os_type": self.os_type,
            "remora_executable_path": self.remora_executable_path,
            "mpi_command": self.mpi_command,
            "default_num_procs": self.default_num_procs,
            "working_directory": self.working_directory,
            "gpu_enabled": self.gpu_enabled,
            "num_gpus": self.num_gpus,
            "gpu_type": self.gpu_type,
            "pre_run_commands": list(self.pre_run_commands),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> MachineProfile:
        """Reconstruct from a dict (e.g. loaded from JSON)."""
        return MachineProfile(
            id=d["id"],
            name=d["name"],
            host_type=d["host_type"],
            hostname=d.get("hostname"),
            port=d.get("port", 22),
            username=d.get("username"),
            auth_method=d.get("auth_method", "key"),
            ssh_key_path=d.get("ssh_key_path"),
            os_type=d.get("os_type", "linux"),
            remora_executable_path=d.get("remora_executable_path", ""),
            mpi_command=d.get("mpi_command", "mpirun"),
            default_num_procs=d.get("default_num_procs", 1),
            working_directory=d.get("working_directory", ""),
            gpu_enabled=d.get("gpu_enabled", False),
            num_gpus=d.get("num_gpus", 0),
            gpu_type=d.get("gpu_type", ""),
            pre_run_commands=d.get("pre_run_commands", []),
        )


# ---------------------------------------------------------------------------
# AppSettings  (JSON-file backend — no Qt dependency)
# ---------------------------------------------------------------------------

_SETTINGS_FILE = "settings.json"


class AppSettings:
    """Persistent application settings backed by a JSON file.

    Parameters
    ----------
    config_dir:
        Directory where ``settings.json`` is stored.  Typically the
        platform-specific app data directory.
    """

    def __init__(self, config_dir: str | Path) -> None:
        self._dir = Path(config_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / _SETTINGS_FILE
        self._data: dict[str, Any] = self._load()

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            return json.loads(self._path.read_text())  # type: ignore[no-any-return]
        return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    # ------------------------------------------------------------------
    # Machine profiles
    # ------------------------------------------------------------------

    def get_machine_profiles(self) -> list[MachineProfile]:
        """Return all saved machine profiles."""
        return [
            MachineProfile.from_dict(d)
            for d in self._data.get("machine_profiles", [])
        ]

    def save_machine_profile(self, profile: MachineProfile) -> None:
        """Insert or update a machine profile (matched by id)."""
        profiles: list[dict[str, Any]] = self._data.setdefault("machine_profiles", [])
        for i, d in enumerate(profiles):
            if d["id"] == profile.id:
                profiles[i] = profile.to_dict()
                self._save()
                return
        profiles.append(profile.to_dict())
        self._save()

    def delete_machine_profile(self, profile_id: str) -> None:
        """Remove a machine profile by id."""
        profiles: list[dict[str, Any]] = self._data.get("machine_profiles", [])
        self._data["machine_profiles"] = [d for d in profiles if d["id"] != profile_id]
        self._save()

    # ------------------------------------------------------------------
    # Default project directory
    # ------------------------------------------------------------------

    def get_default_project_dir(self) -> Path:
        """Return the default base directory for new projects."""
        raw = self._data.get("default_project_dir")
        if raw:
            return Path(raw)
        return Path.home() / "remora_projects"

    def set_default_project_dir(self, path: str | Path) -> None:
        self._data["default_project_dir"] = str(path)
        self._save()

    # ------------------------------------------------------------------
    # Recent projects
    # ------------------------------------------------------------------

    _MAX_RECENT = 10

    def get_recent_projects(self) -> list[str]:
        """Return recently opened project paths (most recent first)."""
        return list(self._data.get("recent_projects", []))

    def add_recent_project(self, path: str | Path) -> None:
        """Push *path* to the front of the recent-projects list."""
        recents: list[str] = self._data.setdefault("recent_projects", [])
        s = str(path)
        if s in recents:
            recents.remove(s)
        recents.insert(0, s)
        self._data["recent_projects"] = recents[: self._MAX_RECENT]
        self._save()
