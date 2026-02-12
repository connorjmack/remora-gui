# REMORA-GUI Implementation Checklist

> Optimized for Claude Code agentic execution. Each task is self-contained with clear
> inputs, outputs, and acceptance criteria. Execute in order — dependencies flow top-down.
>
> **Convention:** Check boxes `[x]` when complete. Sub-tasks indent under their parent.

---

## Phase 0: Project Scaffolding

### 0.1 — Initialize Python package structure
- [x] Create directory tree: `src/remora_gui/`, `src/remora_gui/core/`, `src/remora_gui/ui/`, `src/remora_gui/ui/config_editor/`, `src/remora_gui/ui/execution/`, `src/remora_gui/ui/visualization/`, `src/remora_gui/ui/project/`, `src/remora_gui/ui/dialogs/`, `src/remora_gui/ui/widgets/`, `src/remora_gui/templates/`, `src/remora_gui/resources/`, `src/remora_gui/resources/icons/`, `tests/`, `tests/fixtures/`, `scripts/`
- [x] Add `__init__.py` to every Python package directory
- [x] Create `src/remora_gui/__main__.py` with `def main(): pass` stub and `if __name__ == "__main__"` block

### 0.2 — Create pyproject.toml
- [x] PEP 621 metadata: name=`remora-gui`, version=`0.1.0`, requires-python=`>=3.10`
- [x] Core dependencies: `PyQt6>=6.5`, `numpy>=1.24`, `matplotlib>=3.7`, `xarray>=2023.0`, `netCDF4>=1.6`, `paramiko>=3.0`
- [x] Dev dependencies group `[dev]`: `pytest`, `pytest-qt`, `pytest-cov`, `mypy`, `ruff`, `pre-commit`
- [x] Entry point: `remora-gui = "remora_gui.__main__:main"`
- [x] Editable install: confirm `pip install -e ".[dev]"` succeeds

### 0.3 — Configure tooling
- [x] Add `[tool.ruff]` section in pyproject.toml: target Python 3.10, line-length 100, select rules
- [x] Add `[tool.mypy]` section: strict mode, ignore missing imports for PyQt6
- [x] Add `[tool.pytest.ini_options]`: testpaths=`["tests"]`, qt_api=`"pyqt6"`
- [x] Create `.gitignore` for Python, PyQt, IDE files, `__pycache__`, `.mypy_cache`, `*.egg-info`, `build/`, `dist/`
- [x] Run `ruff check src/ tests/` and `pytest` — both should pass (no files to lint/test yet, no errors)

### 0.4 — Git initialization
- [ ] `git init`, initial commit with scaffolding, PRD, LICENSE, CLAUDE.md, this todo

---

## Phase 1: Core Business Logic (No Qt)

> Everything in `core/` must be testable without a running Qt application.

### 1.1 — REMORAParameter dataclass (`core/parameter_schema.py`)
- [x] Define `REMORAParameter` dataclass with fields: `key`, `label`, `description`, `group`, `dtype` (Literal), `default`, `required`, `min_value`, `max_value`, `enum_options`, `depends_on`, `units`, `reference_url`
- [x] Define `PARAMETER_GROUPS` ordered list: `["domain", "timing", "physics", "mixing", "advection", "boundary", "output", "parallel", "restart"]`
- [x] **Test:** `test_parameter_schema.py` — import dataclass, instantiate one parameter, verify fields

### 1.2 — Complete parameter schema population (`core/parameter_schema.py`)
- [x] Define `PARAMETER_SCHEMA: dict[str, list[REMORAParameter]]` mapping group → parameter list
- [x] Populate **Domain** group (5 params): `prob_lo`, `prob_hi`, `n_cell`, `is_periodic`, `flat_bathymetry` — all from PRD §7.1
- [x] Populate **Timing** group (4 params): `max_step`, `fixed_dt`, `fixed_fast_dt`, `stop_time` — PRD §7.2
- [x] Populate **Physics** group (12 params): `R0`, `rho0`, `S0`, `T0`, `Tcoef`, `Scoef`, `tcline`, `use_coriolis`, `coriolis_type`, `coriolis_f0`, `coriolis_beta`, `use_gravity` — PRD §7.3
- [x] Populate **Mixing** group (8 params): `vertical_mixing_type`, `gls_stability_type`, `gls_P`, `gls_M`, `gls_N`, `Akv_bak`, `Akt_bak`, `Aks_bak` — PRD §7.4
- [x] Populate **Advection** group (2 params): `tracer_horizontal_advection_scheme`, `tracer_vertical_advection_scheme` — PRD §7.5
- [x] Populate **Boundary** group (6 face params): BC type for `xlo`, `xhi`, `ylo`, `yhi`, `zlo`, `zhi` — PRD §7.6
- [x] Populate **Output** group (10 params): `plot_file`, `plot_int`, `plotfile_type`, `plot_vars_3d`, `plot_vars_2d`, `check_file`, `check_int`, `write_history_file`, `sum_interval`, `v` — PRD §7.7
- [x] Populate **Parallel** group (4 params): `max_level`, `ref_ratio`, `max_grid_size`, `blocking_factor` — PRD §7.8
- [x] Populate **Restart** group (1 param): `amr.restart` — PRD §7.9
- [x] Add helper functions: `get_parameter(key) -> REMORAParameter`, `get_group(name) -> list[REMORAParameter]`, `get_defaults() -> dict[str, Any]`
- [x] **Test:** `test_parameter_schema.py`:
  - All parameters have valid `dtype` values
  - No duplicate keys across all groups
  - All defaults are within declared min/max constraints
  - Every group in `PARAMETER_GROUPS` has at least one parameter
  - `get_defaults()` returns dict with correct number of keys
  - `depends_on` references point to keys that exist in the schema

### 1.3 — Input file parser (`core/input_file.py`)
- [x] `parse_input_file(path: str | Path) -> OrderedDict[str, Any]`
  - Skip comment lines (start with `#`) and blank lines
  - Parse `key = value` (spaces around `=` optional)
  - Detect multi-value lines → store as `list` (e.g., `"0.0 0.0 -150.0"` → `[0.0, 0.0, -150.0]`)
  - Detect int vs float vs bool (`true`/`false`) vs string for scalar values
  - Handle inline comments: `key = value # comment` → strip comment
  - Handle quoted strings: `"SlipWall"` → `SlipWall`
  - Preserve parameter ordering
- [x] `parse_input_string(text: str) -> OrderedDict[str, Any]` — same logic, from string instead of file
- [x] Create **test fixtures**: copy the Upwelling example input file to `tests/fixtures/upwelling_inputs`
- [x] **Test:** `test_input_file.py`:
  - Parse fixture file, verify key count, spot-check 5+ values
  - Comment-only lines skipped
  - Inline comments stripped
  - Multi-value parsed as list with correct types
  - Bool parsed as Python `bool`
  - Scientific notation parsed as `float`
  - Quoted strings unquoted

### 1.4 — Input file writer (`core/input_file.py`)
- [x] `write_input_file(params: OrderedDict[str, Any], path: str | Path, schema: dict | None = None, include_defaults: bool = False, header_comment: str | None = None)`
  - Group parameters by prefix (e.g., all `remora.*` together, all `amr.*` together)
  - Write section comment headers between groups
  - Format values: bools → `true`/`false`, lists → space-separated, floats preserve scientific notation where appropriate
  - If `schema` provided and `include_defaults=False`, skip parameters matching their schema default
  - Add `header_comment` at top if provided
- [x] `write_input_string(params: ...) -> str` — same logic, return string
- [x] **Test:** `test_input_file.py`:
  - Round-trip: `parse(write(parse(fixture)))` produces identical dict
  - Bools written as lowercase `true`/`false`
  - Vectors written space-separated
  - Scientific notation preserved for small floats
  - Unknown parameters (not in schema) are preserved through round-trip

### 1.5 — Cross-parameter validator (`core/validator.py`)
- [ ] Define `ValidationMessage` dataclass: `level` (Literal `"error"`, `"warning"`, `"info"`), `message: str`, `parameter_keys: list[str]`, `rule_id: str`
- [ ] Define `validate(params: dict, schema: dict) -> list[ValidationMessage]`
- [ ] Implement rules:
  - `R001`: `fixed_fast_dt` should evenly divide `fixed_dt` → warning
  - `R002`: Periodic faces must match `is_periodic` flags → error
  - `R003`: `n_cell` values must all be > 0 → error
  - `R004`: `prob_hi[i]` must be > `prob_lo[i]` for each dimension → error
  - `R005`: If `use_coriolis=false`, Coriolis sub-params should not be set → info
  - `R006`: `max_grid_size` should be >= `blocking_factor` → warning
- [ ] **Test:** `test_validator.py`:
  - Valid default config → no errors
  - `fixed_dt=300`, `fixed_fast_dt=7` → R001 warning
  - `is_periodic=[1,0,0]` with `xlo.type="SlipWall"` → R002 error
  - `n_cell=[0, 80, 16]` → R003 error
  - `prob_lo=[0,0,0]`, `prob_hi=[0,0,0]` → R004 error

### 1.6 — Project & SimulationRun models (`core/project.py`)
- [ ] Define `SimulationRun` dataclass with all fields from PRD §6.3
- [ ] Define `Project` dataclass with all fields from PRD §6.2
- [ ] `Project.save(path)` → write `project.json` via `dataclasses.asdict` + JSON serialization (handle `datetime`)
- [ ] `Project.load(path) -> Project` → read JSON, reconstruct dataclasses
- [ ] `Project.create_run(name, params) -> SimulationRun` → creates run directory, writes input file, returns run
- [ ] `Project.new(name, description, base_directory) -> Project` → create directory structure: `project.json`, `runs/`, `templates/`
- [ ] **Test:** `test_project.py`:
  - Create project → save → load → verify all fields match
  - Create run → verify directory structure created
  - JSON serialization round-trip with datetimes

### 1.7 — MachineProfile model (`core/settings.py`)
- [ ] Define `MachineProfile` dataclass with all fields from PRD §6.1
- [ ] `MachineProfile.to_dict()` and `MachineProfile.from_dict(d)` for JSON serialization
- [ ] Define `AppSettings` class wrapping `QSettings` (or plain JSON for testing) with:
  - `get_machine_profiles() -> list[MachineProfile]`
  - `save_machine_profile(profile)`, `delete_machine_profile(id)`
  - `get_default_project_dir() -> Path`
  - `get_recent_projects() -> list[str]`
  - `add_recent_project(path)`
- [ ] **Test:** `test_settings.py` — round-trip MachineProfile through dict; AppSettings CRUD with temp dir

### 1.8 — Local execution engine (`core/execution.py`)
- [ ] Define `ExecutionEngine` Protocol/ABC with: `start()`, `stop()`, `is_running() -> bool`, `exit_code() -> int | None`
- [ ] Define signals/callbacks interface: `on_stdout(line: str)`, `on_stderr(line: str)`, `on_finished(exit_code: int)`, `on_progress(step: int, max_step: int)`
- [ ] Implement `LocalExecutionEngine(ExecutionEngine)`:
  - `__init__(executable, input_file, working_dir, mpi_command, num_procs)`
  - `start()`: build command list, spawn via `subprocess.Popen` with pipes, start reader threads
  - `stop()`: SIGTERM → 10s wait → SIGKILL
  - Parse stdout for `Step N` pattern to emit progress
- [ ] **Test:** `test_execution.py`:
  - Mock subprocess: verify command construction for 1 proc (no MPI) and N procs (with MPI)
  - Verify stop sends SIGTERM
  - Verify progress parsing regex extracts step numbers

### 1.9 — Template library data (`templates/`)
- [ ] Create `templates/upwelling.json` — convert Upwelling example params to JSON with metadata: `{"name": "Upwelling", "description": "...", "category": "coastal", "parameters": {...}}`
- [ ] Create `templates/seamount.json` — Seamount example
- [ ] Create `templates/double_gyre.json` — Double Gyre example
- [ ] Create `templates/advection.json` — Advection test
- [ ] Create `templates/blank.json` — blank starting point (only required params with defaults)
- [ ] Add `load_template(name) -> dict` and `list_templates() -> list[dict]` functions in a `core/templates.py` or in `parameter_schema.py`
- [ ] **Test:** all template JSON files parse without error, all contain required metadata keys, all parameter keys exist in schema

---

## Phase 1: UI Layer (PyQt6)

> Depends on all of Phase 1 Core being complete. Each task builds on the previous.

### 2.1 — Application shell (`app.py`, `__main__.py`)
- [ ] `app.py`: `RemoraApp` class — create `QApplication`, set app name/org, apply Fusion style
- [ ] `__main__.py`: `main()` → instantiate `RemoraApp`, show `MainWindow`, exec event loop
- [ ] Verify `python -m remora_gui` launches a window (can be empty)

### 2.2 — Dark theme stylesheet (`resources/style.qss`)
- [ ] Write `style.qss` with dark ocean theme from PRD §9.1:
  - Background `#1e1e2e`, surface `#2a2a3e`, text `#e2e8f0`, muted `#a0aec0`
  - Accent teal `#2c7a7b`, blue `#4299e1`
  - Style: QMainWindow, QTabWidget, QGroupBox, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QPlainTextEdit, QToolBar, QMenuBar, QStatusBar, QScrollArea, QSplitter, QTableWidget, QProgressBar, QToolTip
- [ ] Load stylesheet in `app.py` on startup
- [ ] Verify app renders with dark theme

### 2.3 — Main window skeleton (`ui/main_window.py`)
- [ ] `MainWindow(QMainWindow)` with:
  - Menu bar: File (New Project, Open, Save, Export Input File, Quit), Edit (Preferences), Help (About)
  - Toolbar: New, Open, Save, Run, Stop buttons (icons from QStyle standard pixmaps)
  - Central widget: `QTabWidget` with 3 tabs — "Config", "Run", "Output" (placeholder widgets for now)
  - Status bar: project name label, machine label
  - Keyboard shortcuts from PRD §9.3
- [ ] Connect menu actions to stub slots (print to console for now)
- [ ] Verify window renders with menus, toolbar, tabs, status bar

### 2.4 — Reusable widgets (`ui/widgets/`)
- [ ] `parameter_widget.py`: `ParameterWidget` — factory that creates the right input widget based on `REMORAParameter.dtype`:
  - `int` → `QSpinBox` (set min/max from schema)
  - `float` → `QDoubleSpinBox` with scientific notation support (custom `ScientificSpinBox` subclass with `textFromValue`/`valueFromText` overrides)
  - `bool` → `QCheckBox`
  - `string` → `QLineEdit`
  - `enum` → `QComboBox` with `enum_options`
  - `int_vec3`/`float_vec3` → delegate to `Vector3Widget`
  - `string_list` → `QLineEdit` with space-separated values
  - Each widget: label on left, input on right, tooltip = `description` + `units` + range
  - Signal: `value_changed(key: str, value: Any)`
- [ ] `vector3_widget.py`: `Vector3Widget` — 3 spin boxes in a row with x/y/z labels
  - Support both int and float modes
  - Signal: `value_changed(list[int | float])`
- [ ] `enum_combo.py`: `EnumComboBox` — `QComboBox` wrapper that emits the enum string value
- [ ] `file_picker.py`: `FilePickerWidget` — `QLineEdit` + browse button, returns path string
- [ ] `collapsible_group.py`: `CollapsibleGroupBox` — `QGroupBox` that can collapse/expand its contents with animation
- [ ] **Test:** `test_widgets.py` (pytest-qt) — instantiate each widget, set value, read value back, verify `value_changed` signal fires

### 2.5 — Config editor panel base + auto-generation (`ui/config_editor/`)
- [ ] `base_panel.py`: `ConfigPanel(QScrollArea)` base class:
  - `__init__(group_name: str)` — reads `PARAMETER_SCHEMA[group_name]`, auto-generates `ParameterWidget` for each parameter
  - Handles `depends_on`: connect dependency widget's `value_changed` to show/hide dependent widgets
  - `get_values() -> dict[str, Any]` — collect all current values
  - `set_values(params: dict)` — populate widgets from dict
  - `reset_to_defaults()` — reset all widgets to schema defaults
  - Signal: `values_changed(dict)` — emitted on any widget change
- [ ] `domain_panel.py`: extends `ConfigPanel("domain")`:
  - Adds a computed info box showing Δx, Δy, Δz (auto-updates when `prob_lo`/`prob_hi`/`n_cell` change)
- [ ] `physics_panel.py`: extends `ConfigPanel("physics")` — no special additions
- [ ] `mixing_panel.py`: extends `ConfigPanel("mixing")` — GLS params hidden when mixing_type != gls
- [ ] `boundary_panel.py`: extends `ConfigPanel("boundary")` — 6 dropdowns, one per face
- [ ] `advection_panel.py`: extends `ConfigPanel("advection")`
- [ ] `output_panel.py`: extends `ConfigPanel("output")`
- [ ] `timing_panel.py`: extends `ConfigPanel("timing")`
- [ ] `parallel_panel.py`: extends `ConfigPanel("parallel")`

### 2.6 — Raw text editor (`ui/config_editor/raw_editor.py`)
- [ ] `RawEditor(QWidget)` containing a `QPlainTextEdit` with:
  - Syntax highlighting via `QSyntaxHighlighter`: comments green, keys white, values blue, `=` muted
  - Line numbers (custom `QPlainTextEdit` subclass or gutter widget)
  - Monospace font
- [ ] `get_text() -> str` and `set_text(text: str)`
- [ ] Signal: `text_changed(str)`

### 2.7 — Config editor tab assembly (`ui/config_editor/__init__.py` or `config_tab.py`)
- [ ] `ConfigEditorTab(QWidget)`:
  - Left side: `QTabWidget` (or vertical button bar) with sub-tabs for each panel: Domain, Physics, Mixing, BCs, Advection, Output, Timing, Parallel
  - Right side (togglable): Raw editor panel
  - **Two-way sync**: form changes → update raw text; raw text edits → update form (debounced 500ms)
  - Bottom: validation panel showing `ValidationMessage` list with severity icons, clickable to jump to parameter
- [ ] Wire up to `MainWindow` as the "Config" tab content

### 2.8 — Execution UI (`ui/execution/`)
- [ ] `log_viewer.py`: `LogViewer(QPlainTextEdit)`:
  - Read-only, monospace, auto-scroll to bottom
  - `append_stdout(line)`, `append_stderr(line)` — stderr in red
  - Max 100k lines buffer with pruning
  - Copy/clear buttons
- [ ] `run_panel.py`: `RunPanel(QWidget)`:
  - Machine selector dropdown (populated from `AppSettings.get_machine_profiles()`)
  - MPI process count spinbox
  - Run button (green), Stop button (red)
  - Progress bar (updated from execution engine's `on_progress`)
  - Embedded `LogViewer`
  - Status label: "Ready" / "Running (step 50/1000)" / "Completed (exit 0)" / "Failed (exit 1)"
- [ ] Wire to `LocalExecutionEngine`: Run button → generate input file → `engine.start()` → stream logs
- [ ] Wire up to `MainWindow` as the "Run" tab content

### 2.9 — Dialogs (`ui/dialogs/`)
- [ ] `new_project_dialog.py`: `NewProjectDialog(QDialog)`:
  - Fields: project name, description, base directory (with browse)
  - Template selector (dropdown or grid of cards from `list_templates()`)
  - OK/Cancel buttons
  - On OK: call `Project.new()`, populate config editor from template
- [ ] `template_picker_dialog.py`: `TemplatePickerDialog(QDialog)`:
  - Grid of cards: template name, description, category badge
  - Preview of key parameters on hover/select
  - Select + OK loads template into config editor
- [ ] `machine_config_dialog.py`: `MachineConfigDialog(QDialog)`:
  - List of machine profiles on left, detail form on right
  - Add/Edit/Delete buttons
  - Form fields for all `MachineProfile` fields
  - "Test" button: runs executable with `--help` flag or `echo ok` over SSH
- [ ] `preferences_dialog.py`: `PreferencesDialog(QDialog)`:
  - General tab: default project dir, auto-save interval, theme toggle
  - Machines tab: embed `MachineConfigDialog`
  - Editor tab: font size, show/hide advanced params

### 2.10 — Project browser sidebar (`ui/project/`)
- [ ] `project_browser.py`: `ProjectBrowser(QDockWidget)`:
  - Tree view: Project → Runs (with status icons: draft/running/completed/failed)
  - Right-click context menu: Rename, Delete, Duplicate, Open Output Folder
  - Double-click run → load its params into config editor
- [ ] `run_history.py`: `RunHistory(QWidget)`:
  - Table: run name, status, date, machine, duration, notes
  - Sortable columns
  - Connect to project browser for navigation

### 2.11 — Wire everything together
- [ ] `MainWindow.__init__`: create all panels, connect signals:
  - File > New → `NewProjectDialog` → create project → populate UI
  - File > Open → `QFileDialog` → `Project.load()` → populate UI
  - File > Save → `Project.save()`
  - File > Export → `write_input_file()` → `QFileDialog` for save location
  - Run toolbar button → generate input file → start execution engine
  - Stop toolbar button → `engine.stop()`
  - Config editor `values_changed` → update project's current run params
  - Execution engine signals → update run panel, log viewer, status bar
- [ ] File > Quit → confirm unsaved changes → `QApplication.quit()`
- [ ] Status bar updates: current project name, run status, selected machine

### 2.12 — Smoke test & polish
- [ ] `python -m remora_gui` launches cleanly with dark theme
- [ ] All 9 config panels render with correct widgets and defaults
- [ ] Changing a value in form updates raw editor; editing raw text updates form
- [ ] Validation warnings appear in real-time as values change
- [ ] New project → select Upwelling template → export input file → parse exported file → verify matches template
- [ ] Run with mock/missing REMORA binary → shows clear error message
- [ ] All `pytest` tests pass, `ruff check` clean, `mypy` clean

---

## Phase 2: Remote Execution + Visualization

> Only start after Phase 1 is fully functional.

### 3.1 — Remote execution engine (`core/remote.py`)
- [ ] `RemoteExecutionEngine(ExecutionEngine)`:
  - `connect(profile: MachineProfile)` → establish SSH session via paramiko
  - `upload_input(local_path, remote_path)` → SFTP upload
  - `start()` → execute REMORA command over SSH, stream stdout/stderr back
  - `download_output(remote_dir, local_dir)` → SFTP download with progress callback
  - `stop()` → send kill signal over SSH
  - Handle `pre_run_commands` from MachineProfile
  - Windows path handling: convert paths based on `os_type`
- [ ] Connection pooling: reuse SSH sessions per machine profile
- [ ] Auto-reconnect on dropped connections with retry logic
- [ ] **Test:** `test_remote.py` — mock paramiko, verify command construction, upload/download calls

### 3.2 — Output file reader (`core/output_reader.py`)
- [ ] Define `OutputReader` Protocol with `get_variables()`, `get_dimensions()`, `get_time_steps()`, `get_field()`, `get_slice()`
- [ ] `NetCDFReader(OutputReader)`:
  - Open with `xarray.open_dataset(chunks=...)` for lazy loading
  - Implement all protocol methods
  - Cache recent slices in LRU cache
- [ ] `AMReXReader(OutputReader)`:
  - Parse `Header` file for metadata
  - Read `MultiFab` binary data for selected variables
  - Fallback: try `yt` library if available
- [ ] `open_output(path) -> OutputReader` — auto-detect format and return appropriate reader
- [ ] **Test:** `test_output_reader.py` — create small synthetic NetCDF fixture, verify reads

### 3.3 — 2D slice viewer (`ui/visualization/slice_viewer.py`)
- [ ] Embed `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`
- [ ] Controls: variable dropdown, time step slider, axis selector (X/Y/Z), slice index slider
- [ ] Colormap selector + min/max range inputs
- [ ] Colorbar with units, domain coordinates on axes
- [ ] `NavigationToolbar2QT` for zoom/pan/save
- [ ] Debounce slider updates (100ms)

### 3.4 — Time series viewer (`ui/visualization/timeseries_viewer.py`)
- [ ] Plot variable value at a point over all time steps
- [ ] Click on slice viewer to set probe point
- [ ] Multi-variable overlay with dual y-axes

### 3.5 — Variable explorer (`ui/visualization/variable_explorer.py`)
- [ ] Table: variable name, min, max, mean, units
- [ ] Quick preview thumbnails (surface slice)
- [ ] Double-click → open in slice viewer

### 3.6 — Wire Output tab
- [ ] Output tab: file/directory picker → open output → populate variable explorer
- [ ] Slice viewer + time series viewer in split layout
- [ ] Connect to run completion: auto-open output when run finishes

---

## Phase 3: Experiment Management

### 4.1 — Run history & comparison (`ui/project/run_history.py`)
- [ ] Run history table with sort/filter
- [ ] Parameter diff view: select two runs, side-by-side diff
- [ ] Output comparison: synchronized slice viewers for two runs, difference view

### 4.2 — Parameter sweep (`core/sweep.py` + `ui/dialogs/sweep_dialog.py`)
- [ ] Sweep config dialog: select params, define ranges, show combinatorial matrix
- [ ] Generate all input files upfront
- [ ] Sequential or parallel execution with progress tracking

### 4.3 — Enhanced validation (`core/validator.py`)
- [ ] Add remaining rules from PRD §F3.3 (CFL estimate, domain decomposition, GPU checks)

### 4.4 — Import/Export enhancements
- [ ] Import existing REMORA input files via File > Import
- [ ] Export to JSON, shell script formats
- [ ] Drag-and-drop input file import

---

## Phase 4: Stretch Goals

### 5.1 — 3D visualization (PyVista)
### 5.2 — Visual domain editor (cartopy)
### 5.3 — HPC scheduler integration (Slurm/PBS)
### 5.4 — REMORA build manager

---

## Conventions for agentic execution

1. **One task at a time.** Complete a checkbox, run tests, then move to the next.
2. **Test after every core module.** Never move to the next module without passing tests.
3. **Lint continuously.** Run `ruff check src/ tests/` after every file change.
4. **Type hints everywhere.** All function signatures must have type annotations.
5. **Docstrings on public API.** Every public class/function gets a one-line docstring minimum.
6. **Imports:** `from __future__ import annotations` at top of every file for forward-ref support.
7. **No circular imports.** `core/` never imports from `ui/`. `ui/` imports from `core/`.
8. **Commit after each numbered section** (e.g., after all of 1.2 is done, commit).
