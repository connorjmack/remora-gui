# REMORA-GUI

A cross-platform PyQt6 desktop application for configuring, executing, monitoring, and visualizing simulations from the [REMORA](https://github.com/seahorce-scidac/REMORA) ocean model.

REMORA-GUI treats REMORA as an external dependency — it generates input files, invokes the compiled binary, and reads output files. No REMORA source modifications required.

## Features (Planned)

- **Configuration editor** — validated forms auto-generated from a parameter schema, with defaults, ranges, units, and contextual help
- **Local & remote execution** — launch simulations on the local machine or via SSH to remote workstations
- **Output visualization** — embedded matplotlib plots for NetCDF/AMReX output (slice viewer, time series)
- **Project management** — organize runs, compare configurations, reproduce experiments
- **Templates** — bundled example configs to get started quickly

## Requirements

- Python 3.10+
- A compiled REMORA binary (not included)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
python -m remora_gui
```

## Development

```bash
# Tests
pytest

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/remora_gui/
```

## License

MIT
