# Product Requirements Document: REMORA GUI Wrapper

## Project Codename: **REMORA-GUI**

**Version:** 1.0.0-draft
**Author:** Connor Mack (cjmack@ucsd.edu)
**Date:** 2026-02-12
**Status:** Draft

---

## 1. Executive Summary

REMORA-GUI is a cross-platform desktop application that provides a graphical interface for configuring, executing, monitoring, and visualizing simulations from the REMORA ocean modeling system. REMORA (Regional Earth-system Model Of the Ocean with Reanalysis and Applications) is a C++17 GPU-enabled ocean model built on the AMReX adaptive mesh refinement framework. It solves the Boussinesq hydrostatic Navier-Stokes equations for regional ocean circulation.

Currently, using REMORA requires hand-editing plain-text input files, invoking executables from the command line, and using separate tools for output visualization. REMORA-GUI consolidates this workflow into a single application: researchers configure simulations through validated forms, launch them on local or remote machines, monitor progress in real-time, and visualize results — all without leaving the GUI.

The application is built with **PyQt6** and targets **macOS, Linux, and Windows**. It treats REMORA as an external dependency (no source code modifications) and communicates with it through input file generation, subprocess management, and output file parsing.

---

## 2. Problem Statement

Ocean modelers using REMORA face several friction points:

1. **Manual input file editing** — REMORA's AMReX-format input files contain 100+ parameters across physics, numerics, domain geometry, boundary conditions, and output settings. There is no validation, autocomplete, or contextual help. A single typo causes silent misconfiguration or runtime crashes.

2. **No unified workflow** — Researchers must context-switch between a text editor (input files), a terminal (compilation and execution), and external tools like ParaView or Python scripts (visualization). Each step is disconnected.

3. **Multi-machine execution** — A common setup involves developing/configuring on a laptop (macOS) and executing on a GPU-equipped workstation (Windows/Linux) or HPC cluster. This requires manual file transfer, SSH sessions, and remote monitoring with no integrated tooling.

4. **Steep learning curve** — New users of REMORA must learn the parameter format, valid value ranges, interdependencies between settings, and the full build/run/analyze lifecycle before producing their first simulation. There is no guided onboarding.

5. **No experiment management** — Researchers running parameter sweeps or comparing configurations have no built-in way to organize, tag, diff, or reproduce simulation runs.

---

## 3. Target Users

### Primary Persona: Research Scientist

- Already understands ocean modeling concepts (Navier-Stokes, Coriolis, vertical mixing, etc.)
- Comfortable with terminal usage but prefers efficiency over manual workflows
- Runs REMORA on heterogeneous hardware: macOS laptop for configuration, Windows GPU workstation and/or Linux CPU workstations for execution
- Needs fast iteration: change parameters → run → inspect output → adjust
- Values reproducibility and experiment tracking

### Secondary Persona: Graduate Student / New REMORA User

- Learning ocean modeling; benefits from parameter documentation, defaults, and validation
- May not know which parameters matter for a given problem type
- Needs templates and examples to get started

### Anti-Persona (Out of Scope)

- HPC sysadmins managing batch job schedulers (Slurm, PBS) — the tool may support basic remote execution but is not a full job scheduler frontend
- Developers modifying REMORA's C++ source code — this is a user-facing tool, not an IDE

---

## 4. Hardware & Environment Context

The primary developer/user operates the following environment:

| Machine | OS | Hardware | Role |
|---|---|---|---|
| Laptop | macOS | Apple Silicon (M-series) | GUI host, configuration, visualization, light local runs |
| Workstation A | Windows | NVIDIA GPU(s) | Primary execution target (CUDA-enabled REMORA) |
| Workstation B | Linux | CPU only | Secondary execution target (MPI-parallel CPU runs) |

This means the GUI **must** support remote execution as a first-class feature, not an afterthought. The typical workflow is: configure on Mac → push to Windows/Linux box → execute there → pull results back → visualize on Mac.

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        REMORA-GUI (PyQt6)                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Config       │  │  Execution   │  │  Visualization        │  │
│  │  Editor       │  │  Engine      │  │  Panel                │  │
│  │              │  │              │  │                       │  │
│  │  - Forms     │  │  - Local     │  │  - 2D slice viewer    │  │
│  │  - Validation│  │  - Remote    │  │  - Time series plots  │  │
│  │  - Templates │  │  - Monitoring│  │  - Cross-sections     │  │
│  │  - Import    │  │  - Logs      │  │  - Variable explorer  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                    Core Services Layer                     │  │
│  │                                                           │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ InputFile   │ │ Connection   │ │ Output             │  │  │
│  │  │ Manager     │ │ Manager      │ │ Reader             │  │  │
│  │  │             │ │              │ │                    │  │  │
│  │  │ Parse/write │ │ SSH/local    │ │ NetCDF, AMReX,     │  │  │
│  │  │ AMReX input │ │ file xfer    │ │ checkpoint parsing │  │  │
│  │  │ files       │ │ job control  │ │                    │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │ Project     │ │ Template     │ │ Settings           │  │  │
│  │  │ Manager     │ │ Library      │ │ Store              │  │  │
│  │  │             │ │              │ │                    │  │  │
│  │  │ Experiment  │ │ Bundled      │ │ App prefs,         │  │  │
│  │  │ org, history│ │ REMORA       │ │ machine profiles,  │  │  │
│  │  │ diffing     │ │ examples     │ │ paths              │  │  │
│  │  └─────────────┘ └──────────────┘ └────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │  Local   │ │ Remote   │ │ Remote   │
          │  REMORA  │ │ Windows  │ │ Linux    │
          │  binary  │ │ (GPU)    │ │ (CPU)    │
          └──────────┘ └──────────┘ └──────────┘
```

### 5.2 Directory / Project Structure

```
remora-gui/
├── README.md
├── LICENSE
├── pyproject.toml                  # PEP 621 project metadata + build config
├── requirements.txt                # Pinned dependencies
├── requirements-dev.txt            # Dev/test dependencies
│
├── src/
│   └── remora_gui/
│       ├── __init__.py
│       ├── __main__.py             # Entry point: python -m remora_gui
│       ├── app.py                  # QApplication setup, main window
│       │
│       ├── core/                   # Non-GUI business logic
│       │   ├── __init__.py
│       │   ├── input_file.py       # Parse/write REMORA input files
│       │   ├── parameter_schema.py # Parameter definitions, types, ranges, docs
│       │   ├── validator.py        # Cross-parameter validation rules
│       │   ├── execution.py        # Local subprocess execution engine
│       │   ├── remote.py           # SSH remote execution (paramiko)
│       │   ├── output_reader.py    # NetCDF / AMReX output parsing
│       │   ├── project.py          # Project/experiment management
│       │   └── settings.py         # App settings persistence (QSettings)
│       │
│       ├── ui/                     # PyQt6 widgets and views
│       │   ├── __init__.py
│       │   ├── main_window.py      # Main window with tab/dock layout
│       │   ├── config_editor/      # Input file editor panels
│       │   │   ├── __init__.py
│       │   │   ├── domain_panel.py
│       │   │   ├── physics_panel.py
│       │   │   ├── mixing_panel.py
│       │   │   ├── boundary_panel.py
│       │   │   ├── advection_panel.py
│       │   │   ├── output_panel.py
│       │   │   ├── timing_panel.py
│       │   │   ├── parallel_panel.py
│       │   │   └── raw_editor.py   # Fallback plain-text editor
│       │   ├── execution/          # Run controls and monitoring
│       │   │   ├── __init__.py
│       │   │   ├── run_panel.py
│       │   │   ├── log_viewer.py
│       │   │   └── job_status.py
│       │   ├── visualization/      # Output visualization
│       │   │   ├── __init__.py
│       │   │   ├── plot_panel.py
│       │   │   ├── slice_viewer.py
│       │   │   ├── timeseries_viewer.py
│       │   │   └── variable_explorer.py
│       │   ├── project/            # Project management views
│       │   │   ├── __init__.py
│       │   │   ├── project_browser.py
│       │   │   └── run_history.py
│       │   ├── dialogs/            # Modal dialogs
│       │   │   ├── __init__.py
│       │   │   ├── new_project_dialog.py
│       │   │   ├── machine_config_dialog.py
│       │   │   ├── template_picker_dialog.py
│       │   │   └── preferences_dialog.py
│       │   └── widgets/            # Reusable custom widgets
│       │       ├── __init__.py
│       │       ├── parameter_widget.py    # Smart input for typed params
│       │       ├── vector3_widget.py      # 3-value vector input (x, y, z)
│       │       ├── enum_combo.py          # Dropdown for enum params
│       │       ├── file_picker.py         # Path selection widget
│       │       └── collapsible_group.py   # Collapsible parameter groups
│       │
│       ├── templates/              # Bundled REMORA example configs
│       │   ├── upwelling.json
│       │   ├── seamount.json
│       │   ├── double_gyre.json
│       │   ├── advection.json
│       │   └── blank.json
│       │
│       └── resources/              # Icons, stylesheets, etc.
│           ├── icons/
│           ├── style.qss           # Qt stylesheet
│           └── remora_logo.png
│
├── tests/
│   ├── __init__.py
│   ├── test_input_file.py          # Input file parse/write round-trip
│   ├── test_parameter_schema.py    # Schema validation
│   ├── test_validator.py           # Cross-parameter validation
│   ├── test_output_reader.py       # Output file parsing
│   ├── test_execution.py           # Subprocess management
│   └── fixtures/                   # Sample input/output files
│       ├── upwelling_inputs
│       ├── seamount_inputs
│       └── sample_output.nc
│
└── scripts/
    ├── build_remora.sh             # Helper: clone + build REMORA
    └── package.sh                  # PyInstaller / cx_Freeze packaging
```

### 5.3 Key Design Principles

1. **REMORA is an external dependency.** The GUI never modifies REMORA source code. It generates input files, invokes the compiled executable, and reads output files. If REMORA's input format changes, only `parameter_schema.py` and `input_file.py` need updating.

2. **Separation of core logic and UI.** Everything in `core/` is GUI-agnostic and independently testable. The `ui/` layer consumes `core/` services. This enables future alternative frontends (CLI, web) without rewriting business logic.

3. **Machine profiles are first-class.** Because execution happens on different machines, the concept of a "machine profile" (hostname, OS, path to REMORA binary, available GPUs, MPI configuration) is a core data model, not a bolt-on.

4. **Offline-capable.** The GUI works fully offline for local execution. Remote features degrade gracefully (clear error messages) when the network is unavailable.

---

## 6. Data Models

### 6.1 Machine Profile

Stored in app settings. Defines a target execution environment.

```python
@dataclass
class MachineProfile:
    id: str                          # UUID
    name: str                        # User-friendly label, e.g. "GPU Workstation"
    host_type: Literal["local", "remote"]

    # Remote-only fields
    hostname: str | None             # e.g. "192.168.1.50" or "gpu-box.local"
    port: int = 22
    username: str | None
    auth_method: Literal["key", "password", "agent"] = "key"
    ssh_key_path: str | None         # Path to private key

    # Execution environment
    os_type: Literal["linux", "macos", "windows"]
    remora_executable_path: str      # Absolute path on the target machine
    mpi_command: str = "mpirun"      # Or "mpiexec", "srun", etc.
    default_num_procs: int = 1
    working_directory: str           # Where input/output files live on target

    # Optional GPU config
    gpu_enabled: bool = False
    num_gpus: int = 0
    gpu_type: str = ""               # Informational, e.g. "NVIDIA RTX 4090"

    # Environment setup (run before REMORA)
    pre_run_commands: list[str] = field(default_factory=list)
    # e.g. ["module load cuda/12.0", "export PATH=$PATH:/opt/remora/bin"]
```

### 6.2 Project

A project represents a collection of related simulation runs.

```python
@dataclass
class Project:
    id: str                          # UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    base_directory: str              # Local directory for project files
    runs: list[SimulationRun]
```

### 6.3 Simulation Run

A single execution of REMORA with a specific configuration.

```python
@dataclass
class SimulationRun:
    id: str                          # UUID
    project_id: str
    name: str                        # User-assigned label
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    status: Literal["draft", "queued", "running", "completed", "failed", "cancelled"]

    # Configuration
    input_parameters: dict           # Full parameter dict
    input_file_path: str             # Path to generated input file
    machine_profile_id: str          # Which machine to run on
    num_procs: int                   # MPI process count

    # Execution metadata
    pid: int | None                  # Process ID (local) or remote job ID
    exit_code: int | None
    log_path: str | None             # Path to captured stdout/stderr

    # Results
    output_directory: str | None     # Where plotfiles / NetCDF output landed
    checkpoint_path: str | None      # Latest checkpoint (for restart)
    notes: str = ""                  # User annotations
    tags: list[str] = field(default_factory=list)
```

### 6.4 REMORA Parameter

Defines a single configurable parameter with metadata for UI generation.

```python
@dataclass
class REMORAParameter:
    key: str                         # e.g. "remora.fixed_dt"
    label: str                       # e.g. "Time Step (dt)"
    description: str                 # Tooltip / help text
    group: str                       # UI grouping: "domain", "physics", etc.

    # Type and constraints
    dtype: Literal["int", "float", "bool", "string", "enum",
                    "int_vec3", "float_vec3", "string_list"]
    default: Any
    required: bool = False

    # Validation
    min_value: float | None = None
    max_value: float | None = None
    enum_options: list[str] | None = None   # Valid string values

    # Dependencies
    depends_on: dict | None = None   # e.g. {"remora.use_coriolis": True}
    # Only show/enable this param when the dependency is satisfied

    # Documentation
    units: str | None = None         # e.g. "seconds", "kg/m³", "m"
    reference_url: str | None = None # Link to REMORA docs
```

---

## 7. REMORA Parameter Schema (Complete)

This section defines every parameter group the Config Editor must support. This is the most critical section for implementation — it directly maps to UI panels and input file generation.

### 7.1 Domain Geometry (`domain_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Domain Lower Bound | `remora.prob_lo` | float_vec3 | `0.0 0.0 -150.0` | meters | z_lo < 0 (depth) | Lower corner of computational domain (x, y, z) |
| Domain Upper Bound | `remora.prob_hi` | float_vec3 | `41000.0 80000.0 0.0` | meters | z_hi = 0 (surface) | Upper corner of computational domain (x, y, z) |
| Grid Cells | `remora.n_cell` | int_vec3 | `41 80 16` | — | all > 0 | Number of grid cells in each direction |
| Periodicity | `remora.is_periodic` | int_vec3 | `1 0 0` | — | 0 or 1 each | Periodic boundary in each direction (1=periodic) |
| Flat Bathymetry | `remora.flat_bathymetry` | bool | `false` | — | — | If true, use flat bottom (no topography) |

### 7.2 Time Stepping (`timing_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Max Steps | `remora.max_step` | int | `10` | — | > 0 | Total number of baroclinic time steps |
| Fixed Time Step | `remora.fixed_dt` | float | `300.0` | seconds | > 0 | Baroclinic (3D) time step size |
| Fast Time Step | `remora.fixed_fast_dt` | float | `10.0` | seconds | > 0, should divide fixed_dt evenly | Barotropic (2D) sub-step size |
| Stop Time | `remora.stop_time` | float | — | seconds | > 0 | Alternative to max_step: stop at this sim time |

**Cross-Validation Rule:** `fixed_dt` should be an integer multiple of `fixed_fast_dt`. The validator should warn (not block) if this is not the case.

### 7.3 Physics (`physics_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Reference Density | `remora.R0` | float | `1027.0` | kg/m³ | > 0 | Background density for EOS |
| Mean Density | `remora.rho0` | float | `1025.0` | kg/m³ | > 0 | Mean ocean density |
| Reference Salinity | `remora.S0` | float | `35.0` | PSU | >= 0 | Reference salinity for linear EOS |
| Reference Temperature | `remora.T0` | float | `14.0` | °C | — | Reference temperature for linear EOS |
| Thermal Expansion Coeff | `remora.Tcoef` | float | `1.7e-4` | 1/°C | >= 0 | Thermal expansion coefficient |
| Haline Contraction Coeff | `remora.Scoef` | float | `0.0` | 1/PSU | >= 0 | Haline contraction coefficient |
| Thermocline Depth | `remora.tcline` | float | `25.0` | meters | > 0 | Thermocline depth for S-coordinate stretching |
| Use Coriolis | `remora.use_coriolis` | bool | `true` | — | — | Enable Coriolis force |
| Coriolis Type | `remora.coriolis_type` | enum | `beta_plane` | — | `beta_plane`, `custom` | Type of Coriolis parameterization |
| Coriolis f₀ | `remora.coriolis_f0` | float | `-8.26e-5` | 1/s | — | Reference Coriolis parameter (depends_on: use_coriolis=true) |
| Coriolis β | `remora.coriolis_beta` | float | `0.0` | 1/(m·s) | — | Beta-plane gradient (depends_on: use_coriolis=true) |
| Use Gravity | `remora.use_gravity` | bool | `true` | — | — | Enable gravitational acceleration |

### 7.4 Vertical Mixing (`mixing_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Mixing Type | `remora.vertical_mixing_type` | enum | `gls` | — | `gls`, `analytic` | Vertical mixing parameterization |
| GLS Stability Type | `remora.gls_stability_type` | enum | `galperin` | — | `galperin`, `kantha_clayson`, etc. | GLS stability function (depends_on: mixing_type=gls) |
| GLS p | `remora.gls_P` | float | `3.0` | — | — | GLS parameter p |
| GLS m | `remora.gls_M` | float | `1.5` | — | — | GLS parameter m |
| GLS n | `remora.gls_N` | float | `-1.0` | — | — | GLS parameter n |
| Background Viscosity | `remora.Akv_bak` | float | `1.0e-5` | m²/s | >= 0 | Background vertical viscosity |
| Background Temp Diff | `remora.Akt_bak` | float | `1.0e-6` | m²/s | >= 0 | Background vertical diffusivity for temperature |
| Background Salt Diff | `remora.Aks_bak` | float | `1.0e-6` | m²/s | >= 0 | Background vertical diffusivity for salinity |

### 7.5 Advection Schemes (`advection_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Tracer Horiz Advection | `remora.tracer_horizontal_advection_scheme` | enum | `upstream3` | — | `upstream3`, `centered4` | Horizontal advection scheme for tracers |
| Tracer Vert Advection | `remora.tracer_vertical_advection_scheme` | enum | `upstream3` | — | `upstream3`, `centered4` | Vertical advection scheme for tracers |

### 7.6 Boundary Conditions (`boundary_panel.py`)

Each of the 6 faces has a type and optional associated data. The UI should present a visual representation of the 3D domain with clickable faces.

**Per-face parameters** (repeat for `xlo`, `xhi`, `ylo`, `yhi`, `zlo`, `zhi`):

| Parameter | Key Pattern | Type | Default | Constraints | Description |
|---|---|---|---|---|---|
| BC Type | `remora.bc.{face}.type` | enum | — | See list below | Boundary condition type for this face |

**Valid BC types:** `SlipWall`, `NoSlipWall`, `Outflow`, `Clamped`, `Chapman`, `Flather`, `Periodic`, `Orlanski`, `OrlankiNudg`

**Cross-Validation Rule:** If `remora.is_periodic[i] = 1`, the corresponding face pair (e.g., xlo/xhi) must not have explicit BC types set, or they must be `Periodic`. The validator should enforce this.

### 7.7 Output Configuration (`output_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Plot File Prefix | `remora.plot_file` | string | `plt` | — | valid filename chars | Prefix for plotfile directory names |
| Plot Interval | `remora.plot_int` | int | `100` | steps | > 0 or -1 (disabled) | Steps between plotfile writes |
| Plot File Type | `remora.plotfile_type` | enum | `amrex` | — | `amrex`, `netcdf`, `hdf5` | Output format |
| 3D Plot Variables | `remora.plot_vars_3d` | string_list | `salt temp x_velocity y_velocity z_velocity` | — | valid var names | Which 3D fields to output |
| 2D Plot Variables | `remora.plot_vars_2d` | string_list | — | — | valid var names | Which 2D fields to output |
| Checkpoint Prefix | `remora.check_file` | string | `chk` | — | valid filename chars | Prefix for checkpoint directories |
| Checkpoint Interval | `remora.check_int` | int | `-57600` | steps or seconds | negative=wall-clock seconds | Steps between checkpoints (negative = wall-clock time) |
| Write History File | `remora.write_history_file` | bool | `false` | — | depends_on: plotfile_type=netcdf | Write NetCDF history file |
| Diagnostic Interval | `remora.sum_interval` | int | `1` | steps | >= 0 | Steps between diagnostic summaries |
| Verbosity | `remora.v` | int | `0` | — | 0-2 | Console output verbosity |

### 7.8 AMR / Parallelism (`parallel_panel.py`)

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Max AMR Level | `amr.max_level` | int | `0` | — | >= 0 | Maximum refinement level (0 = no AMR) |
| Refinement Ratio | `amr.ref_ratio` | int | `2` | — | 2 or 4 | Grid refinement ratio between levels |
| Max Grid Size | `amr.max_grid_size` | int | `2048` | cells | > 0 | Max cells per grid box (affects load balancing) |
| Blocking Factor | `amr.blocking_factor` | int | `1` | cells | > 0, power of 2 | Grid cells must be divisible by this |

### 7.9 Restart Configuration

| Parameter | Key | Type | Default | Units | Constraints | Description |
|---|---|---|---|---|---|---|
| Restart From | `amr.restart` | string | — | — | valid checkpoint name | Checkpoint directory to restart from |

---

## 8. Feature Specifications by Phase

### Phase 1: Configuration Editor + Local Execution (MVP)

**Goal:** A usable application that replaces hand-editing input files and provides one-click local execution with live log streaming.

**Duration estimate:** 4-6 weeks

#### F1.1 — Application Shell

- **Main window** with a menu bar, toolbar, and tabbed central widget
- **Tab layout:** Config Editor | Run | Output (tabs are always visible; content populates as features are built)
- **Menu bar:** File (New Project, Open, Save, Export Input File, Quit), Edit (Preferences), Help (About, REMORA Docs link)
- **Toolbar:** New, Open, Save, Run, Stop buttons
- **Status bar:** Shows current project name, last save time, connection status to remote machines
- **Settings persistence:** Use `QSettings` to remember window geometry, last opened project, recent files

**Implementation notes:**
- `app.py`: Create `QApplication`, apply `style.qss`, instantiate `MainWindow`
- `main_window.py`: `QMainWindow` with `QTabWidget` central widget, `QMenuBar`, `QToolBar`, `QStatusBar`
- `style.qss`: Dark theme with ocean-inspired accent colors (deep blue `#1a365d`, teal `#2c7a7b`, white text). Use Qt's fusion style as the base.

#### F1.2 — Parameter Schema Engine

- Define all REMORA parameters as `REMORAParameter` dataclass instances in `parameter_schema.py`
- Organize parameters into groups matching UI panels
- Each parameter carries: key, label, description (for tooltips), type, default, validation constraints, units, conditional dependencies
- Schema is the single source of truth — both the UI and the input file writer consume it

**Implementation notes:**
- `parameter_schema.py`: Define a `PARAMETER_SCHEMA: dict[str, list[REMORAParameter]]` mapping group names to parameter lists
- Include all parameters from Section 7 of this document
- Support `depends_on` for conditional visibility (e.g., GLS params only shown when mixing_type=gls)
- Include `units` strings for display in the UI

#### F1.3 — Config Editor Panels

Each parameter group gets a dedicated panel (see Section 5.2 for file mapping). All panels share these behaviors:

- **Auto-generated from schema:** Panels iterate over `PARAMETER_SCHEMA[group]` and create appropriate widgets per `dtype`
- **Widget mapping:**
  - `int` → `QSpinBox`
  - `float` → `QDoubleSpinBox` (with scientific notation support via custom widget)
  - `bool` → `QCheckBox`
  - `string` → `QLineEdit`
  - `enum` → `QComboBox`
  - `int_vec3` / `float_vec3` → `Vector3Widget` (3 spin boxes in a row with x/y/z labels)
  - `string_list` → `QLineEdit` with space-separated values + tag-style display
- **Tooltips:** Every widget has a tooltip showing `description` + `units` + valid range
- **Validation:** Real-time. Invalid values highlighted in red. Validation errors shown in a panel at the bottom of the editor.
- **Conditional visibility:** Parameters with `depends_on` are hidden/disabled when their dependency is not met
- **Defaults:** All fields pre-populated with defaults from schema. User changes are visually marked (bold label or accent border).

**Special panels:**

- **Domain panel** (`domain_panel.py`): Include a simple schematic showing the 3D box with labeled dimensions. Update dynamically as `prob_lo`, `prob_hi`, `n_cell` change. Show computed cell sizes (Δx, Δy, Δz).
- **Boundary panel** (`boundary_panel.py`): Show a 2D schematic of the domain faces. Each face is a clickable region that opens a dropdown for BC type selection. Color-coded by BC type.
- **Raw editor** (`raw_editor.py`): A `QPlainTextEdit` with syntax highlighting for the AMReX input format. Two-way sync: changes in the form update the raw text and vice versa. This is the escape hatch for advanced users or parameters not yet in the schema.

#### F1.4 — Input File Parser / Writer

- **Parse:** Read an existing REMORA input file into a `dict[str, Any]`
  - Handle comments (lines starting with `#`)
  - Handle multi-value parameters (`remora.prob_lo = 0.0 0.0 -150.0` → list)
  - Handle quoted string values
  - Handle inline comments
  - Preserve unknown parameters (pass through without losing them)
- **Write:** Serialize a parameter dict back to AMReX input format
  - Group parameters by prefix for readability
  - Include section comment headers
  - Include units in inline comments for documentation
  - Only write parameters that differ from defaults (with an option to write all)

**Implementation notes:**
- `input_file.py`: Two main functions: `parse_input_file(path: str) -> dict` and `write_input_file(params: dict, path: str, include_defaults: bool = False)`
- Round-trip fidelity: `parse(write(parse(file)))` should produce identical output
- Unit tests with fixtures from actual REMORA example problems

#### F1.5 — Template Library

- Bundle the 16 REMORA example problems as JSON templates in `templates/`
- Each template contains: name, description, category, parameter overrides (relative to defaults), and a thumbnail/icon
- Template picker dialog: grid of cards showing template name, description, thumbnail
- Selecting a template populates the Config Editor with those parameter values
- Templates are read-only; selecting one creates a copy for the user to modify

**Bundled templates (from REMORA's `Exec/` directory):**
1. Upwelling — Wind-driven coastal upwelling
2. Seamount — Flow around an isolated seamount
3. Double Gyre — Wind-driven double gyre circulation
4. Advection — Simple tracer advection test
5. Channel Test — Channel flow
6. Boundary Layer — Boundary layer dynamics
7. Doubly Periodic — Doubly periodic domain
8. Blank Problem — Empty starting point

**Implementation notes:**
- Convert each `Exec/*/inputs` file to JSON via `parse_input_file`
- Store as `templates/*.json` with additional metadata fields (name, description, category)
- `template_picker_dialog.py`: `QDialog` with a `QGridLayout` of template cards

#### F1.6 — Local Execution Engine

- **Launch:** Spawn REMORA as a subprocess via `subprocess.Popen`
  - Construct command: `[mpi_command, "-np", str(num_procs), remora_path, input_file_path]`
  - If `num_procs == 1`, skip MPI wrapper
  - Set working directory to the project's run directory
  - Capture `stdout` and `stderr` via pipes
- **Live log streaming:** Read stdout/stderr in a background `QThread` and emit signals to update the log viewer widget in real-time
- **Stop/Cancel:** Send `SIGTERM` to the process group. If it doesn't exit in 10 seconds, send `SIGKILL`.
- **Completion detection:** Monitor process exit. On completion, update run status, parse exit code, check for output files.
- **Progress estimation:** Parse REMORA's stdout for time step numbers (format: `Step N`). Show progress as `current_step / max_step` in a progress bar.

**Implementation notes:**
- `execution.py`: `LocalExecutionEngine` class with `start()`, `stop()`, `is_running()` methods
- Use `QThread` + signals for non-blocking log streaming
- `run_panel.py`: Contains the "Run" button, MPI proc count spinner, machine selector dropdown, progress bar, and embedded log viewer
- `log_viewer.py`: `QPlainTextEdit` in read-only mode with auto-scroll and ANSI color parsing

#### F1.7 — Project Management (Basic)

- **New project** creates a directory structure:
  ```
  my_project/
  ├── project.json          # Project metadata
  ├── runs/
  │   └── run_001/
  │       ├── inputs         # Generated input file
  │       ├── run.json       # Run metadata
  │       └── output/        # Symlink or copy of output directory
  └── templates/             # User-saved custom templates
  ```
- **Save/Load** projects via JSON serialization of `Project` and `SimulationRun` dataclasses
- **Open recent** list in File menu
- **Export input file** writes the current configuration as a standalone AMReX input file (for use outside the GUI)

#### F1.8 — Preferences Dialog

- **General tab:** Default project directory, auto-save interval, theme selection
- **Machines tab:** CRUD interface for Machine Profiles (see Section 6.1). List on left, detail form on right.
  - For local machines: just the REMORA executable path, MPI command, and default num_procs
  - Includes a "Test" button that runs `remora_path --help` or a trivial input to verify the binary works
- **Editor tab:** Font size for raw editor, show/hide advanced parameters

---

### Phase 2: Remote Execution + Output Visualization

**Goal:** Execute REMORA on remote Windows/Linux machines from the Mac GUI, and visualize simulation output.

**Duration estimate:** 4-6 weeks

#### F2.1 — Remote Execution via SSH

- **SSH connection management** using `paramiko` library
  - Connect using key-based auth (default), password, or SSH agent
  - Connection pooling: maintain persistent SSH sessions per machine profile
  - Auto-reconnect on dropped connections
- **File transfer:**
  - Upload: Copy generated input file + any required data files to the remote machine's working directory via SFTP
  - Download: Pull output files (plotfiles, NetCDF, logs) back to the local machine after run completion
  - Transfer progress bar for large output files
- **Remote execution:**
  - Execute REMORA command over SSH: `ssh user@host "cd /path/to/workdir && mpirun -np N /path/to/remora inputs"`
  - Stream stdout/stderr back over the SSH channel to the local log viewer
  - Support `pre_run_commands` from MachineProfile (e.g., `module load cuda`)
- **Windows-specific handling:**
  - Windows machines may use OpenSSH server or WSL
  - Support both native Windows paths (`C:\REMORA\...`) and WSL paths (`/mnt/c/REMORA/...`)
  - Machine profile includes a `path_style` field: `posix` or `windows`
- **Job persistence:**
  - If the GUI is closed while a remote job is running, record the PID and SSH session info
  - On next launch, offer to reconnect and resume monitoring

**Implementation notes:**
- `remote.py`: `RemoteExecutionEngine` class mirroring the `LocalExecutionEngine` interface
  - `connect()`, `upload_input()`, `start()`, `stream_logs()`, `download_output()`, `stop()`
  - Uses `paramiko.SSHClient` for commands and `paramiko.SFTPClient` for file transfer
- `machine_config_dialog.py`: Add "Test Connection" button that SSH connects and runs `echo ok`
- Both `LocalExecutionEngine` and `RemoteExecutionEngine` implement a common `ExecutionEngine` protocol/ABC so the UI code doesn't care which one is active

#### F2.2 — Output File Reader

- **NetCDF reader** (primary, recommended output format):
  - Use `xarray` to open NetCDF datasets
  - Extract variable names, dimensions, time steps, coordinate arrays
  - Support lazy loading (don't load entire dataset into memory)
  - Handle both single-file and history-file formats
- **AMReX native reader** (secondary):
  - Parse the `Header` file to get metadata (variable names, levels, box layout)
  - Read `MultiFab` binary data for selected variables/levels
  - Use `yt` library as a fallback if direct parsing is too complex
- **Common interface:** Both readers produce a uniform data structure:
  ```python
  @dataclass
  class SimulationOutput:
      variables: list[str]           # e.g. ["temp", "salt", "x_velocity"]
      dimensions: dict[str, int]     # e.g. {"x": 41, "y": 80, "z": 16}
      time_steps: list[float]        # Simulation times for each output
      coordinates: dict[str, np.ndarray]  # x, y, z coordinate arrays

      def get_field(self, variable: str, time_index: int) -> np.ndarray:
          """Return 3D array for a given variable at a given time step."""
          ...

      def get_slice(self, variable: str, time_index: int,
                     axis: str, index: int) -> np.ndarray:
          """Return 2D slice along an axis."""
          ...
  ```

**Implementation notes:**
- `output_reader.py`: `NetCDFReader` and `AMReXReader` classes both implementing `OutputReader` protocol
- Lazy-load with `xarray.open_dataset(chunks=...)` for large files
- Cache recent data slices in memory for responsive scrubbing through time steps

#### F2.3 — 2D Visualization Panel

- **Slice viewer** (`slice_viewer.py`):
  - Embed a `matplotlib` `FigureCanvas` in the PyQt panel
  - Controls: variable selector (dropdown), time step slider, axis selector (X/Y/Z), slice index slider
  - Colormap selector (viridis, plasma, coolwarm, etc.) with min/max range inputs
  - Auto-update as controls change
  - Colorbar with units
  - Domain coordinates on axes (not just grid indices)
- **Time series viewer** (`timeseries_viewer.py`):
  - Plot a variable's value at a specific point over all time steps
  - Click on the slice viewer to set the probe point
  - Multi-variable overlay (e.g., temperature and salinity on dual y-axes)
- **Variable explorer** (`variable_explorer.py`):
  - Table showing all output variables with: name, min, max, mean, units
  - Quick preview thumbnails for each variable (surface slice)
  - Double-click a variable to open it in the slice viewer

**Implementation notes:**
- Use `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` for embedding
- `NavigationToolbar2QT` for zoom/pan/save controls
- Debounce slider updates (100ms) to avoid excessive redraws during scrubbing
- Consider `matplotlib.animation.FuncAnimation` for playback mode (animate through time steps)

---

### Phase 3: Experiment Management + Quality of Life

**Goal:** Support parameter sweeps, run comparison, and polish the workflow for daily research use.

**Duration estimate:** 3-4 weeks

#### F3.1 — Run History & Comparison

- **Run history panel** (`run_history.py`):
  - Table showing all runs in the current project: name, status, date, machine, duration, notes
  - Sort and filter by any column
  - Right-click context menu: rename, delete, duplicate, export, open output folder
- **Parameter diff view:**
  - Select two runs and see a side-by-side diff of their input parameters
  - Only show parameters that differ (with toggle to show all)
  - Color-coded: green for additions, red for removals, yellow for changes
- **Output comparison:**
  - Load two runs' output side-by-side in the slice viewer
  - Synchronized controls: same variable, time step, slice — different runs
  - Difference view: compute and display `run_A[var] - run_B[var]`

#### F3.2 — Parameter Sweep

- **Sweep configuration dialog:**
  - Select 1-3 parameters to sweep
  - For each: define a range (start, end, step) or explicit list of values
  - Show the full combinatorial matrix with total run count
  - Name template for generated runs (e.g., `sweep_dt{fixed_dt}_visc{Akv_bak}`)
- **Sweep execution:**
  - Generate all input files upfront
  - Execute sequentially or in parallel (user-configurable max concurrent runs)
  - Track sweep progress in a dedicated sweep status panel
  - On completion, auto-open comparison view

#### F3.3 — Configuration Validation Engine (Enhanced)

- **Cross-parameter validation rules** in `validator.py`:
  1. `fixed_fast_dt` should evenly divide `fixed_dt` → warning
  2. Periodic faces must have matching `is_periodic` flags → error
  3. `n_cell` values should be compatible with `max_grid_size` and `blocking_factor` → warning
  4. CFL condition estimate: `dt * max_velocity / dx < 1` → warning (requires velocity estimate input)
  5. `num_procs` should evenly divide the domain decomposition → warning
  6. GPU run with `num_procs` > num_gpus → warning
- **Validation panel:** Persistent panel at bottom of Config Editor showing all warnings/errors with severity icons. Click a warning to jump to the relevant parameter.

#### F3.4 — Import / Export

- **Import existing REMORA input file:** File > Import reads any valid REMORA input file and populates the editor. Unknown parameters are preserved in the raw editor.
- **Export formats:**
  - AMReX input file (default)
  - JSON (for programmatic use or version control)
  - Shell script (complete run command with all parameters as CLI overrides)
- **Drag-and-drop:** Drop a REMORA input file onto the window to import it

---

### Phase 4: Advanced Features (Stretch Goals)

**Goal:** 3D visualization, domain editor, HPC scheduler integration, and build management.

**Duration estimate:** 6-8 weeks (lower priority, implement as needed)

#### F4.1 — 3D Visualization

- Use `PyVista` (VTK wrapper) for 3D rendering
- Volume rendering of scalar fields (temperature, salinity)
- Isosurface extraction
- Streamlines for velocity fields
- Interactive rotation, zoom, clipping planes
- Export rendered frames as PNG or animated GIF

#### F4.2 — Visual Domain Editor

- 2D map view (using `cartopy` or simple matplotlib) showing the domain extent
- Click-and-drag to set `prob_lo` and `prob_hi` on a geographic map
- Bathymetry overlay from ETOPO1 or similar dataset
- Grid resolution preview showing cell sizes on the map

#### F4.3 — HPC Scheduler Integration

- Support Slurm (`sbatch`), PBS (`qsub`), and LSF (`bsub`)
- Job script template editor with variable substitution
- Submit, monitor, cancel jobs through the GUI
- Parse scheduler output for job ID, status, queue position

#### F4.4 — REMORA Build Manager

- Clone REMORA from GitHub (or use existing checkout)
- Configure build options through the GUI (CMake flags)
- Compile on local or remote machines
- Track multiple builds (different flags, compilers, GPU vs CPU)
- Associate builds with machine profiles

---

## 9. UI/UX Specifications

### 9.1 Visual Design

- **Theme:** Dark mode by default (reduces eye strain during long research sessions). Light mode available as a toggle.
- **Color palette:**
  - Background: `#1e1e2e` (dark navy)
  - Surface: `#2a2a3e` (slightly lighter)
  - Primary accent: `#2c7a7b` (teal — ocean theme)
  - Secondary accent: `#4299e1` (bright blue)
  - Error: `#fc8181` (soft red)
  - Warning: `#f6e05e` (yellow)
  - Success: `#68d391` (green)
  - Text: `#e2e8f0` (off-white)
  - Muted text: `#a0aec0` (gray)
- **Typography:** System font (SF Pro on macOS, Segoe UI on Windows, DejaVu Sans on Linux). Monospace for the raw editor and log viewer (JetBrains Mono or Fira Code if available, else system mono).
- **Icons:** Use `QStyle.StandardPixmap` where possible; custom SVG icons for domain-specific actions (play, stop, sweep, etc.)
- **Layout:** Dense but not cramped. Research tools should show information, not hide it behind extra clicks.

### 9.2 Main Window Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Menu Bar: File | Edit | View | Run | Help                        │
├──────────────────────────────────────────────────────────────────┤
│ Toolbar: [New] [Open] [Save] [|] [Run ▶] [Stop ■] [|] [Machine ▼]│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┬────────────────────────────────────────┐    │
│  │  Project         │  Config Editor | Run | Output          │    │
│  │  Browser         │                                        │    │
│  │  (Left Dock)     │  ┌──────────────────────────────────┐  │    │
│  │                  │  │                                  │  │    │
│  │  ▾ Project A     │  │  [Domain] [Physics] [Mixing]     │  │    │
│  │    ▸ Run 001     │  │  [BCs] [Advection] [Output]      │  │    │
│  │    ▸ Run 002     │  │  [Timing] [Parallel] [Raw]       │  │    │
│  │    ▾ Run 003     │  │                                  │  │    │
│  │      inputs      │  │  ┌────────────────────────────┐  │  │    │
│  │      output/     │  │  │  Domain Geometry            │  │    │
│  │      log.txt     │  │  │                            │  │  │    │
│  │                  │  │  │  Domain Lower Bound (m)    │  │  │    │
│  │  ▾ Project B     │  │  │  [  0.0  ] [  0.0  ] [-150]│  │  │    │
│  │    ...           │  │  │                            │  │  │    │
│  │                  │  │  │  Domain Upper Bound (m)    │  │  │    │
│  │                  │  │  │  [41000 ] [80000 ] [ 0.0 ] │  │  │    │
│  │                  │  │  │                            │  │  │    │
│  │                  │  │  │  Grid Cells                │  │  │    │
│  │                  │  │  │  [ 41 ]   [ 80 ]   [ 16 ] │  │  │    │
│  │                  │  │  │                            │  │  │    │
│  │                  │  │  │  Cell Size: Δx=1000m ...   │  │  │    │
│  │                  │  │  └────────────────────────────┘  │  │    │
│  │                  │  │                                  │  │    │
│  │                  │  │  ┌────────────────────────────┐  │  │    │
│  │                  │  │  │  ⚠ Warnings (2)            │  │  │    │
│  │                  │  │  │  fast_dt doesn't divide dt │  │  │    │
│  │                  │  │  └────────────────────────────┘  │  │    │
│  │                  │  │                                  │  │    │
│  └─────────────────┴──┴──────────────────────────────────┘  │    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Status: Project A — Run 003 (draft) │ Machine: GPU Workstation   │
└──────────────────────────────────────────────────────────────────┘
```

### 9.3 Keyboard Shortcuts

| Action | Shortcut |
|---|---|
| New Project | `Ctrl+N` |
| Open Project | `Ctrl+O` |
| Save | `Ctrl+S` |
| Run Simulation | `Ctrl+R` or `F5` |
| Stop Simulation | `Ctrl+Shift+R` or `Shift+F5` |
| Export Input File | `Ctrl+E` |
| Toggle Raw Editor | `Ctrl+Shift+E` |
| Preferences | `Ctrl+,` |
| Switch to Config tab | `Ctrl+1` |
| Switch to Run tab | `Ctrl+2` |
| Switch to Output tab | `Ctrl+3` |

---

## 10. Technical Requirements

### 10.1 Python Version

- **Minimum:** Python 3.10 (for `match` statements, `X | Y` union types, `dataclass` improvements)
- **Recommended:** Python 3.11+ (for performance and `tomllib`)

### 10.2 Dependencies

**Core (required):**

| Package | Version | Purpose |
|---|---|---|
| `PyQt6` | >= 6.5 | GUI framework |
| `numpy` | >= 1.24 | Numerical arrays |
| `matplotlib` | >= 3.7 | 2D plotting and embedded figures |
| `xarray` | >= 2023.0 | NetCDF output reading |
| `netCDF4` | >= 1.6 | NetCDF file I/O backend |
| `paramiko` | >= 3.0 | SSH remote execution |
| `appdirs` | >= 1.4 | Cross-platform app directory resolution |

**Optional (for specific features):**

| Package | Version | Purpose | Phase |
|---|---|---|---|
| `pyvista` | >= 0.40 | 3D visualization | Phase 4 |
| `yt` | >= 4.2 | AMReX native format reading | Phase 2 (fallback) |
| `cartopy` | >= 0.22 | Geographic map projections | Phase 4 |
| `h5py` | >= 3.8 | HDF5 output reading | Phase 2 |
| `scipy` | >= 1.10 | Interpolation, analysis | Phase 3 |
| `pyinstaller` | >= 6.0 | Application packaging | Release |

### 10.3 Development Dependencies

| Package | Purpose |
|---|---|
| `pytest` | Unit testing |
| `pytest-qt` | PyQt widget testing |
| `pytest-cov` | Code coverage |
| `mypy` | Static type checking |
| `ruff` | Linting and formatting |
| `pre-commit` | Git hook management |

### 10.4 Build & Packaging

- **Distribution:** `pyproject.toml` using `hatchling` or `setuptools` backend
- **Entry point:** `remora-gui = "remora_gui.__main__:main"`
- **Standalone packaging:** PyInstaller for creating distributable executables per platform
- **Version scheme:** Semantic versioning (MAJOR.MINOR.PATCH)

---

## 11. Non-Functional Requirements

### 11.1 Performance

- **Startup time:** < 3 seconds to main window on modern hardware
- **Input file generation:** < 100ms for any configuration
- **Log streaming latency:** < 500ms from REMORA stdout to GUI display
- **Output file loading:** < 5 seconds for a 500MB NetCDF file (lazy loading, show progress)
- **Slice rendering:** < 200ms for a single 2D slice redraw
- **UI responsiveness:** Never block the main thread for > 100ms. All I/O, computation, and network operations run in `QThread` workers.

### 11.2 Reliability

- **Crash recovery:** Auto-save project state every 60 seconds. On crash, offer to restore last auto-save.
- **Graceful degradation:** If SSH connection drops mid-run, show clear error and offer to reconnect. Don't lose the local project state.
- **Input validation:** Prevent generation of input files that would cause REMORA to crash on known issues (see validation rules in Section 8, F3.3).

### 11.3 Portability

- **macOS:** Primary development platform. Apple Silicon (arm64) and Intel (x86_64).
- **Windows:** Must work on Windows 10/11. Handle Windows path separators. PyQt6 is cross-platform; no platform-specific UI code.
- **Linux:** Ubuntu 22.04+, Fedora 38+, Debian 12+. Standard X11/Wayland support via Qt.

### 11.4 Accessibility

- **Keyboard navigation:** All controls reachable via Tab/Shift+Tab
- **Tooltips:** Every parameter widget has a descriptive tooltip
- **Font scaling:** Respect system DPI and font size settings
- **High contrast:** Ensure sufficient contrast ratios in both dark and light themes

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Module | Test Focus |
|---|---|
| `test_input_file.py` | Round-trip parse/write for all example input files. Edge cases: comments, blank lines, unknown parameters, quoted strings. |
| `test_parameter_schema.py` | All parameters have valid types, defaults within constraints, no duplicate keys, all groups have at least one parameter. |
| `test_validator.py` | Each cross-validation rule triggers correctly. Test both valid and invalid configurations. |
| `test_output_reader.py` | Read sample NetCDF files. Verify variable names, dimensions, data values against known outputs. |
| `test_execution.py` | Mock subprocess execution. Verify command construction, log parsing, progress extraction. |
| `test_project.py` | Create, save, load, modify projects. Verify JSON serialization round-trip. |

### 12.2 Integration Tests

- **End-to-end local run:** Load a template → generate input file → verify file matches expected output → (optionally) run REMORA if binary is available
- **Remote execution mock:** Use a local SSH server (or paramiko mock) to test the full upload → execute → download cycle
- **UI smoke tests:** Use `pytest-qt` to verify all panels render without errors, all controls are interactive, menu actions work

### 12.3 Manual Test Scenarios

1. Fresh install: launch app, no REMORA binary configured → preferences dialog guides setup
2. Load Upwelling template → modify 3 parameters → save → export input file → diff against expected
3. Configure remote Windows machine → test connection → run simulation → view output
4. Import a user's existing REMORA input file with unknown parameters → verify nothing lost
5. Kill REMORA mid-run → verify GUI recovers cleanly, logs are preserved, status is "cancelled"
6. Open a 2GB NetCDF output file → verify lazy loading, no memory explosion

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| REMORA input format changes in future versions | Medium | High — breaks file generation | Abstract all parameters through schema layer. Version-tag schemas. Monitor REMORA releases. |
| Windows SSH setup is non-trivial for users | High | Medium — blocks remote execution | Provide setup guide. Support WSL as alternative. Include "Test Connection" with diagnostics. |
| Large output files cause memory issues | Medium | Medium — crashes or freezes | Lazy loading via xarray chunks. Never load full dataset. Stream slices on demand. |
| PyQt6 license concerns for distribution | Low | Medium — limits distribution | PyQt6 is GPL; if commercial distribution needed, switch to PySide6 (LGPL). Same API. |
| Matplotlib rendering too slow for large grids | Medium | Low — poor UX | Downsample for display (show every Nth point). Pre-render at multiple resolutions. |
| Users have different REMORA versions | High | Medium — parameter mismatch | Schema versioning. Allow unknown parameters. Warn on version mismatch if detectable. |

---

## 14. Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Time to first simulation | < 5 minutes from app install | Timed user test with template |
| Config errors from typos | Zero | Input validation catches all known issues |
| Context switches per run | 1 (stay in GUI) | vs. current 3+ (editor, terminal, vis tool) |
| Parameter change → output view | < 10 minutes for small 2D problems | End-to-end workflow timing |

---

## 15. Open Questions

1. **REMORA version compatibility:** Should the GUI target a specific REMORA version (e.g., the current `main` branch) or attempt to be version-agnostic? Recommendation: target current `main` + one version back, with a schema versioning system.

2. **GPU monitoring:** Should the GUI show GPU utilization during runs on the Windows machine? This would require `nvidia-smi` parsing over SSH. Nice to have but not essential.

3. **Collaborative features:** Any need for sharing projects or configurations with collaborators (e.g., export/import project bundles)? For now, the project directory is portable and can be shared via Git or file transfer.

4. **REMORA compilation:** Should Phase 1 include the ability to compile REMORA from source, or is it safe to assume users have a pre-compiled binary? Recommendation: assume pre-compiled for Phase 1; add build manager in Phase 4.

---

## Appendix A: REMORA Input File Format Reference

The AMReX ParmParse format used by REMORA input files:

```ini
# This is a comment
# Blank lines are ignored

# Parameters use prefix.key = value format
remora.max_step = 1000

# Vectors are space-separated
remora.prob_lo = 0.0 0.0 -150.0

# Strings can be quoted
remora.bc.ylo.type = "SlipWall"

# Booleans are true/false (lowercase)
remora.use_coriolis = true

# Scientific notation
remora.Tcoef = 1.7e-4

# Parameters can also be passed as command-line arguments:
# ./REMORA.3d.gnu.ex inputs remora.max_step=2000 remora.fixed_dt=150.0
```

**Parsing rules:**
- Lines starting with `#` are comments
- Empty/whitespace-only lines are ignored
- Format: `key = value` (spaces around `=` are optional)
- Multiple values on one line are space-separated (represent arrays/vectors)
- Quoted strings preserve spaces: `"Slip Wall"` (though REMORA typically uses no-space enums)
- Command-line arguments override file values (no `=` spaces allowed on CLI)
- Unknown parameters are silently ignored by REMORA (but the GUI should preserve them)

---

## Appendix B: Valid REMORA Output Variables

**3D fields (selectable for `plot_vars_3d`):**
`salt`, `temp`, `scalar`, `x_velocity`, `y_velocity`, `z_velocity`, `omega`, `tke`, `gls`

**2D fields (selectable for `plot_vars_2d`):**
`zeta` (free surface), `ubar` (barotropic x-velocity), `vbar` (barotropic y-velocity)

**Diagnostic fields (auto-computed if requested):**
`Akv` (vertical viscosity), `Akt` (vertical diffusivity), `sustr` (surface u-stress), `svstr` (surface v-stress)

---

## Appendix C: Machine Profile Examples

**Local macOS (for testing with small problems):**
```json
{
  "name": "MacBook Local",
  "host_type": "local",
  "os_type": "macos",
  "remora_executable_path": "/usr/local/bin/REMORA.3d.gnu.Release.ex",
  "mpi_command": "mpirun",
  "default_num_procs": 4,
  "working_directory": "~/remora_runs",
  "gpu_enabled": false
}
```

**Remote Windows GPU workstation:**
```json
{
  "name": "GPU Workstation",
  "host_type": "remote",
  "hostname": "192.168.1.50",
  "port": 22,
  "username": "connor",
  "auth_method": "key",
  "ssh_key_path": "~/.ssh/id_rsa",
  "os_type": "windows",
  "remora_executable_path": "C:\\REMORA\\build\\Release\\REMORA.3d.ex",
  "mpi_command": "mpiexec",
  "default_num_procs": 1,
  "working_directory": "C:\\REMORA\\runs",
  "gpu_enabled": true,
  "num_gpus": 1,
  "gpu_type": "NVIDIA RTX 4090",
  "pre_run_commands": []
}
```

**Remote Linux CPU workstation:**
```json
{
  "name": "Linux CPU Cluster",
  "host_type": "remote",
  "hostname": "linux-ws.lab.ucsd.edu",
  "port": 22,
  "username": "cjmack",
  "auth_method": "key",
  "ssh_key_path": "~/.ssh/id_ed25519",
  "os_type": "linux",
  "remora_executable_path": "/opt/remora/bin/REMORA.3d.gnu.Release.MPI.ex",
  "mpi_command": "mpirun",
  "default_num_procs": 32,
  "working_directory": "/scratch/cjmack/remora_runs",
  "gpu_enabled": false,
  "pre_run_commands": ["module load openmpi/4.1", "module load pnetcdf"]
}
```
