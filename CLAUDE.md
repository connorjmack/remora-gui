# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

REMORA-GUI is a cross-platform PyQt6 desktop application for configuring, executing, monitoring, and visualizing simulations from the REMORA ocean model (C++17/AMReX). It treats REMORA as an external dependency — generates input files, invokes the compiled binary, reads output files. No REMORA source modifications.

**Status:** Greenfield — the PRD (`PRD.md`) is the source of truth for requirements and architecture. Implementation follows `docs/todo.md` (seeded from PRD tasks).

## Build & Run Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the application
python -m remora_gui

# Run all tests
pytest

# Run a single test file
pytest tests/test_input_file.py

# Run a specific test
pytest tests/test_input_file.py::test_parse_round_trip -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/remora_gui/
```

## Architecture

**Key principle:** `core/` is GUI-agnostic business logic; `ui/` is PyQt6 presentation. Everything in `core/` must be independently testable without Qt.

```
src/remora_gui/
├── __main__.py              # Entry point
├── app.py                   # QApplication setup, main window init
├── core/                    # Business logic (no Qt imports)
│   ├── input_file.py        # Parse/write AMReX-format input files
│   ├── parameter_schema.py  # Single source of truth for all REMORA parameters
│   ├── validator.py         # Cross-parameter validation rules
│   ├── execution.py         # Local subprocess engine (QThread-based log streaming)
│   ├── remote.py            # SSH remote execution via paramiko
│   ├── output_reader.py     # NetCDF (xarray) and AMReX output parsing
│   ├── project.py           # Project/experiment management, JSON serialization
│   └── settings.py          # App settings via QSettings
├── ui/                      # PyQt6 widgets
│   ├── main_window.py       # QMainWindow with tabs: Config | Run | Output
│   ├── config_editor/       # One panel per parameter group (auto-generated from schema)
│   ├── execution/           # Run controls, log viewer, job status
│   ├── visualization/       # matplotlib-embedded slice viewer, time series, variable explorer
│   ├── project/             # Project browser, run history
│   ├── dialogs/             # Modal dialogs (new project, machine config, preferences)
│   └── widgets/             # Reusable: parameter_widget, vector3_widget, enum_combo, etc.
├── templates/               # Bundled REMORA example configs as JSON
└── resources/               # Icons, style.qss, logo
```

## Critical Design Decisions

- **Parameter schema drives everything.** `parameter_schema.py` defines all REMORA parameters with types, defaults, ranges, units, dependencies, and docs. Both UI panels and input file generation consume it. When REMORA's format changes, only `parameter_schema.py` and `input_file.py` need updates.
- **Machine profiles are first-class.** Users configure on macOS, execute on remote Windows (GPU) or Linux (CPU) machines. The `MachineProfile` dataclass (host, OS, paths, MPI config, pre-run commands) is a core data model.
- **Local and remote execution share an interface.** `LocalExecutionEngine` and `RemoteExecutionEngine` implement a common `ExecutionEngine` protocol/ABC.
- **Input file round-trip fidelity.** `parse(write(parse(file)))` must produce identical output. Unknown parameters are preserved (pass-through).

## Tech Stack

- **Python 3.10+** (uses `match`, `X | Y` unions, dataclass features)
- **PyQt6** (GUI), **matplotlib** (2D plots), **xarray/netCDF4** (output reading), **paramiko** (SSH)
- **pytest + pytest-qt** (testing), **ruff** (lint/format), **mypy** (types)

## REMORA Input File Format

AMReX ParmParse format: `prefix.key = value`. Vectors are space-separated. Comments start with `#`. Booleans are lowercase `true`/`false`. Scientific notation supported (e.g., `1.7e-4`). See PRD Appendix A for full spec.

## Phased Implementation

- **Phase 1 (MVP):** Config editor + local execution + project management + templates
- **Phase 2:** Remote SSH execution + output visualization (NetCDF/AMReX readers + matplotlib)
- **Phase 3:** Experiment management, parameter sweeps, run comparison
- **Phase 4 (stretch):** 3D viz (PyVista), visual domain editor, HPC scheduler integration

## UI Theme

Dark mode default. Ocean-inspired palette: background `#1e1e2e`, teal accent `#2c7a7b`, blue accent `#4299e1`. Qt Fusion style base with custom `style.qss`.
