"""Main application window for REMORA-GUI."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from remora_gui.core.export import export_json, export_shell_script
from remora_gui.core.input_file import parse_input_file, write_input_file
from remora_gui.core.project import Project
from remora_gui.core.settings import AppSettings
from remora_gui.core.templates import load_template
from remora_gui.ui.config_editor.config_tab import ConfigEditorTab
from remora_gui.ui.dialogs.new_project_dialog import NewProjectDialog
from remora_gui.ui.dialogs.preferences_dialog import PreferencesDialog
from remora_gui.ui.execution.run_panel import RunPanel
from remora_gui.ui.project.project_browser import ProjectBrowser
from remora_gui.ui.visualization.output_tab import OutputTab


class MainWindow(QMainWindow):
    """Top-level window with menus, toolbar, tabs, and status bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("REMORA-GUI")
        self.resize(1200, 800)
        self.setAcceptDrops(True)

        self._project: Project | None = None
        self._settings = AppSettings()

        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_tabs()
        self._create_status_bar()
        self._create_project_browser()

    # ---- Actions ----

    def _create_actions(self) -> None:
        """Create all QActions with shortcuts."""
        self.action_new = QAction("&New Project", self)
        self.action_new.setShortcut(QKeySequence("Ctrl+N"))
        self.action_new.triggered.connect(self._on_new_project)

        self.action_open = QAction("&Open Project...", self)
        self.action_open.setShortcut(QKeySequence("Ctrl+O"))
        self.action_open.triggered.connect(self._on_open_project)

        self.action_import = QAction("&Import Input File...", self)
        self.action_import.setShortcut(QKeySequence("Ctrl+I"))
        self.action_import.triggered.connect(self._on_import)

        self.action_save = QAction("&Save", self)
        self.action_save.setShortcut(QKeySequence("Ctrl+S"))
        self.action_save.triggered.connect(self._on_save)

        self.action_export = QAction("&Export Input File...", self)
        self.action_export.setShortcut(QKeySequence("Ctrl+E"))
        self.action_export.triggered.connect(self._on_export)

        self.action_export_json = QAction("Export &JSON...", self)
        self.action_export_json.triggered.connect(self._on_export_json)

        self.action_export_shell = QAction("Export &Shell Script...", self)
        self.action_export_shell.triggered.connect(self._on_export_shell)

        self.action_quit = QAction("&Quit", self)
        self.action_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self.action_quit.triggered.connect(self.close)

        self.action_preferences = QAction("P&references...", self)
        self.action_preferences.setShortcut(QKeySequence("Ctrl+,"))
        self.action_preferences.triggered.connect(self._on_preferences)

        self.action_run = QAction("&Run", self)
        self.action_run.setShortcut(QKeySequence("F5"))
        self.action_run.triggered.connect(self._on_run)

        self.action_stop = QAction("S&top", self)
        self.action_stop.setShortcut(QKeySequence("Shift+F5"))
        self.action_stop.setEnabled(False)
        self.action_stop.triggered.connect(self._on_stop)

        self.action_about = QAction("&About REMORA-GUI", self)
        self.action_about.triggered.connect(self._on_about)

    # ---- Menu Bar ----

    def _create_menu_bar(self) -> None:
        """Build the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_open)
        file_menu.addAction(self.action_import)
        file_menu.addSeparator()
        file_menu.addAction(self.action_save)
        file_menu.addAction(self.action_export)
        file_menu.addAction(self.action_export_json)
        file_menu.addAction(self.action_export_shell)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_preferences)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.action_about)

    # ---- Toolbar ----

    def _create_toolbar(self) -> None:
        """Build the main toolbar."""
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_run)
        toolbar.addAction(self.action_stop)

    # ---- Tabs ----

    def _create_tabs(self) -> None:
        """Create the central tab widget with Config, Run, and Output tabs."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.config_tab = ConfigEditorTab()
        self.run_tab = RunPanel()
        self.output_tab = OutputTab()

        self.tabs.addTab(self.config_tab, "Config")
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.output_tab, "Output")

    # ---- Status Bar ----

    def _create_status_bar(self) -> None:
        """Build the status bar with project and machine labels."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.status_project_label = QLabel("No project")
        self.status_machine_label = QLabel("Local")
        status_bar.addWidget(self.status_project_label)
        status_bar.addPermanentWidget(self.status_machine_label)

    # ---- Project Browser ----

    def _create_project_browser(self) -> None:
        """Create the project browser dock widget."""
        self.project_browser = ProjectBrowser(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_browser)

    # ---- Slots ----

    def _on_new_project(self) -> None:
        dlg = NewProjectDialog(
            default_dir=str(self._settings.get_default_project_dir()),
            parent=self,
        )
        if dlg.exec() != NewProjectDialog.DialogCode.Accepted:
            return
        name = dlg.project_name()
        if not name:
            return
        project = Project.new(
            name=name,
            description=dlg.project_description(),
            base_directory=Path(dlg.base_directory()),
        )
        self._set_project(project)

        # Load template if selected.
        template_file = dlg.selected_template()
        if template_file:
            t = load_template(template_file)
            self.config_tab.set_all_values(t.get("parameters", {}))

    def _on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Project files (project.json)"
        )
        if not path:
            return
        project = Project.load(Path(path))
        self._set_project(project)

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Input File",
            "",
            "REMORA Input Files (*);;All Files (*)",
        )
        if not path:
            return
        try:
            params = parse_input_file(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import Error", str(exc))
            return
        self.config_tab.set_all_values(params)
        self.statusBar().showMessage(f"Imported {len(params)} parameters from {path}", 3000)

    def _on_save(self) -> None:
        if self._project is None:
            return
        self._project.save()
        self.statusBar().showMessage("Saved.", 3000)

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Input File", "inputs", "All Files (*)"
        )
        if not path:
            return
        params = OrderedDict(self.config_tab.get_all_values())
        write_input_file(params, Path(path))
        self.statusBar().showMessage(f"Exported to {path}", 3000)

    def _on_export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "config.json", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        params = OrderedDict(self.config_tab.get_all_values())
        export_json(params, Path(path))
        self.statusBar().showMessage(f"Exported JSON to {path}", 3000)

    def _on_export_shell(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Shell Script", "run.sh", "Shell Scripts (*.sh);;All Files (*)"
        )
        if not path:
            return
        params = OrderedDict(self.config_tab.get_all_values())
        export_shell_script(params, Path(path))
        self.statusBar().showMessage(f"Exported shell script to {path}", 3000)

    def _on_preferences(self) -> None:
        dlg = PreferencesDialog(self._settings, parent=self)
        dlg.exec()

    def _on_run(self) -> None:
        self.tabs.setCurrentWidget(self.run_tab)
        self.run_tab.set_status("Running...")

    def _on_stop(self) -> None:
        self.run_tab.set_status("Stopping...")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About REMORA-GUI",
            "REMORA-GUI v0.1.0\n\n"
            "A cross-platform desktop application for configuring,\n"
            "executing, and monitoring REMORA ocean simulations.",
        )

    # ---- Drag and Drop ----

    def dragEnterEvent(self, event: object) -> None:  # type: ignore[override]
        """Accept drag events for input files."""
        if hasattr(event, "mimeData") and event.mimeData().hasUrls():  # type: ignore[union-attr]
            event.acceptProposedAction()  # type: ignore[union-attr]

    def dropEvent(self, event: object) -> None:  # type: ignore[override]
        """Handle dropped files by importing them."""
        if not hasattr(event, "mimeData"):
            return
        urls = event.mimeData().urls()  # type: ignore[union-attr]
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path:
            try:
                params = parse_input_file(path)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Import Error", str(exc))
                return
            self.config_tab.set_all_values(params)
            self.statusBar().showMessage(
                f"Imported {len(params)} parameters from {path}", 3000
            )

    # ---- Helpers ----

    def _set_project(self, project: Project) -> None:
        """Load a project into the UI."""
        self._project = project
        self.setWindowTitle(f"REMORA-GUI — {project.name}")
        self.status_project_label.setText(project.name)
        self.project_browser.set_project(project)
        self._settings.add_recent_project(str(project.path))
