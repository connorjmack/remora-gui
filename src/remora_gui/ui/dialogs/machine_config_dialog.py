"""Machine configuration dialog — CRUD for MachineProfile entries."""

from __future__ import annotations

import uuid

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from remora_gui.core.settings import AppSettings, MachineProfile


class MachineConfigDialog(QDialog):
    """Dialog for managing machine profiles."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Machine Configuration")
        self.setMinimumSize(700, 500)
        self._settings = settings
        self._current_profile: MachineProfile | None = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter()
        layout.addWidget(splitter)

        # -- Left: profile list --
        left = QWidget()
        left_layout = QVBoxLayout()
        left.setLayout(left_layout)

        self._profile_list = QListWidget()
        self._profile_list.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self._profile_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_profile)
        btn_row.addWidget(add_btn)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        # -- Right: detail form --
        right = QWidget()
        self._form = QFormLayout()
        right.setLayout(self._form)

        self._name_edit = QLineEdit()
        self._form.addRow("Name:", self._name_edit)

        self._host_type_combo = QComboBox()
        self._host_type_combo.addItems(["local", "ssh"])
        self._form.addRow("Host type:", self._host_type_combo)

        self._hostname_edit = QLineEdit()
        self._form.addRow("Hostname:", self._hostname_edit)

        self._username_edit = QLineEdit()
        self._form.addRow("Username:", self._username_edit)

        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(22)
        self._form.addRow("SSH port:", self._port_spin)

        self._key_path_edit = QLineEdit()
        self._form.addRow("Key path:", self._key_path_edit)

        self._os_type_combo = QComboBox()
        self._os_type_combo.addItems(["linux", "macos", "windows"])
        self._form.addRow("OS type:", self._os_type_combo)

        self._exe_path_edit = QLineEdit()
        self._form.addRow("REMORA executable:", self._exe_path_edit)

        self._mpi_cmd_edit = QLineEdit()
        self._mpi_cmd_edit.setText("mpirun")
        self._form.addRow("MPI command:", self._mpi_cmd_edit)

        self._work_dir_edit = QLineEdit()
        self._form.addRow("Working directory:", self._work_dir_edit)

        self._gpu_enabled = QCheckBox("GPU enabled")
        self._form.addRow(self._gpu_enabled)

        self._gpu_count_spin = QSpinBox()
        self._gpu_count_spin.setRange(0, 64)
        self._form.addRow("GPU count:", self._gpu_count_spin)

        self._pre_run_edit = QPlainTextEdit()
        self._pre_run_edit.setMaximumHeight(80)
        self._pre_run_edit.setPlaceholderText("One command per line...")
        self._form.addRow("Pre-run commands:", self._pre_run_edit)

        splitter.addWidget(right)
        splitter.setSizes([200, 500])

        # -- Save / Close --
        save_btn = QPushButton("Save Profile")
        save_btn.clicked.connect(self._save_profile)
        layout.addWidget(save_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_profiles()

    def _load_profiles(self) -> None:
        self._profile_list.clear()
        for p in self._settings.get_machine_profiles():
            item = QListWidgetItem(p.name)
            item.setData(256, p.id)
            self._profile_list.addItem(item)

    def _on_profile_selected(
        self, current: QListWidgetItem | None, _prev: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        profile_id = current.data(256)
        for p in self._settings.get_machine_profiles():
            if p.id == profile_id:
                self._current_profile = p
                self._populate_form(p)
                break

    def _populate_form(self, p: MachineProfile) -> None:
        self._name_edit.setText(p.name)
        self._host_type_combo.setCurrentText(p.host_type)
        self._hostname_edit.setText(p.hostname)
        self._username_edit.setText(p.username)
        self._port_spin.setValue(p.ssh_port)
        self._key_path_edit.setText(p.ssh_key_path)
        self._os_type_combo.setCurrentText(p.os_type)
        self._exe_path_edit.setText(p.remora_executable)
        self._mpi_cmd_edit.setText(p.mpi_command)
        self._work_dir_edit.setText(p.working_directory)
        self._gpu_enabled.setChecked(p.gpu_enabled)
        self._gpu_count_spin.setValue(p.gpu_count)
        self._pre_run_edit.setPlainText("\n".join(p.pre_run_commands))

    def _add_profile(self) -> None:
        new_profile = MachineProfile(
            id=str(uuid.uuid4()),
            name="New Machine",
        )
        self._settings.save_machine_profile(new_profile)
        self._load_profiles()

    def _delete_profile(self) -> None:
        if self._current_profile:
            self._settings.delete_machine_profile(self._current_profile.id)
            self._current_profile = None
            self._load_profiles()

    def _save_profile(self) -> None:
        if self._current_profile is None:
            return
        pre_run = [
            line.strip()
            for line in self._pre_run_edit.toPlainText().splitlines()
            if line.strip()
        ]
        updated = MachineProfile(
            id=self._current_profile.id,
            name=self._name_edit.text(),
            host_type=self._host_type_combo.currentText(),
            hostname=self._hostname_edit.text(),
            username=self._username_edit.text(),
            ssh_port=self._port_spin.value(),
            ssh_key_path=self._key_path_edit.text(),
            os_type=self._os_type_combo.currentText(),
            remora_executable=self._exe_path_edit.text(),
            mpi_command=self._mpi_cmd_edit.text(),
            working_directory=self._work_dir_edit.text(),
            gpu_enabled=self._gpu_enabled.isChecked(),
            gpu_count=self._gpu_count_spin.value(),
            pre_run_commands=pre_run,
        )
        self._settings.save_machine_profile(updated)
        self._load_profiles()
