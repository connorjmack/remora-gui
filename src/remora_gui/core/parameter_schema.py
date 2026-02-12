"""REMORA parameter schema — single source of truth for all simulation parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class REMORAParameter:
    """Definition of a single REMORA simulation parameter."""

    key: str
    label: str
    description: str
    group: str

    # Type and constraints
    dtype: Literal[
        "int", "float", "bool", "string", "enum",
        "int_vec3", "float_vec3", "string_list",
    ]
    default: Any

    required: bool = False

    # Validation
    min_value: float | None = None
    max_value: float | None = None
    enum_options: list[str] | None = field(default=None)

    # Dependencies
    depends_on: dict[str, Any] | None = field(default=None)

    # Documentation
    units: str | None = None
    reference_url: str | None = None


PARAMETER_GROUPS: list[str] = [
    "domain",
    "timing",
    "physics",
    "mixing",
    "advection",
    "boundary",
    "output",
    "parallel",
    "restart",
]

# ---------------------------------------------------------------------------
# Domain Geometry (PRD §7.1)
# ---------------------------------------------------------------------------

_DOMAIN_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.prob_lo",
        label="Domain Lower Bound",
        description="Lower corner of computational domain (x, y, z).",
        group="domain",
        dtype="float_vec3",
        default=[0.0, 0.0, -150.0],
        required=True,
        units="m",
    ),
    REMORAParameter(
        key="remora.prob_hi",
        label="Domain Upper Bound",
        description="Upper corner of computational domain (x, y, z).",
        group="domain",
        dtype="float_vec3",
        default=[41000.0, 80000.0, 0.0],
        required=True,
        units="m",
    ),
    REMORAParameter(
        key="remora.n_cell",
        label="Grid Cells",
        description="Number of grid cells in each direction.",
        group="domain",
        dtype="int_vec3",
        default=[41, 80, 16],
        required=True,
    ),
    REMORAParameter(
        key="remora.is_periodic",
        label="Periodicity",
        description="Periodic boundary in each direction (1=periodic, 0=not).",
        group="domain",
        dtype="int_vec3",
        default=[1, 0, 0],
        required=True,
    ),
    REMORAParameter(
        key="remora.flat_bathymetry",
        label="Flat Bathymetry",
        description="If true, use flat bottom (no topography).",
        group="domain",
        dtype="bool",
        default=False,
    ),
]

# ---------------------------------------------------------------------------
# Time Stepping (PRD §7.2)
# ---------------------------------------------------------------------------

_TIMING_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.max_step",
        label="Max Steps",
        description="Total number of baroclinic time steps.",
        group="timing",
        dtype="int",
        default=10,
        required=True,
        min_value=1,
    ),
    REMORAParameter(
        key="remora.fixed_dt",
        label="Fixed Time Step",
        description="Baroclinic (3D) time step size.",
        group="timing",
        dtype="float",
        default=300.0,
        required=True,
        min_value=0.0,
        units="s",
    ),
    REMORAParameter(
        key="remora.fixed_fast_dt",
        label="Fast Time Step",
        description="Barotropic (2D) sub-step size. Should evenly divide the fixed time step.",
        group="timing",
        dtype="float",
        default=10.0,
        required=True,
        min_value=0.0,
        units="s",
    ),
    REMORAParameter(
        key="remora.stop_time",
        label="Stop Time",
        description="Alternative to max steps: stop at this physical time.",
        group="timing",
        dtype="float",
        default=None,
        min_value=0.0,
        units="s",
    ),
]

# ---------------------------------------------------------------------------
# Physics (PRD §7.3)
# ---------------------------------------------------------------------------

_PHYSICS_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.R0",
        label="Reference Density",
        description="Background density for equation of state.",
        group="physics",
        dtype="float",
        default=1027.0,
        min_value=0.0,
        units="kg/m³",
    ),
    REMORAParameter(
        key="remora.rho0",
        label="Mean Density",
        description="Mean ocean density.",
        group="physics",
        dtype="float",
        default=1025.0,
        min_value=0.0,
        units="kg/m³",
    ),
    REMORAParameter(
        key="remora.S0",
        label="Reference Salinity",
        description="Reference salinity for linear equation of state.",
        group="physics",
        dtype="float",
        default=35.0,
        min_value=0.0,
        units="PSU",
    ),
    REMORAParameter(
        key="remora.T0",
        label="Reference Temperature",
        description="Reference temperature for linear equation of state.",
        group="physics",
        dtype="float",
        default=14.0,
        units="°C",
    ),
    REMORAParameter(
        key="remora.Tcoef",
        label="Thermal Expansion Coeff",
        description="Thermal expansion coefficient.",
        group="physics",
        dtype="float",
        default=1.7e-4,
        min_value=0.0,
        units="1/°C",
    ),
    REMORAParameter(
        key="remora.Scoef",
        label="Haline Contraction Coeff",
        description="Haline contraction coefficient.",
        group="physics",
        dtype="float",
        default=0.0,
        min_value=0.0,
        units="1/PSU",
    ),
    REMORAParameter(
        key="remora.tcline",
        label="Thermocline Depth",
        description="Thermocline depth for S-coordinate stretching.",
        group="physics",
        dtype="float",
        default=25.0,
        min_value=0.0,
        units="m",
    ),
    REMORAParameter(
        key="remora.use_coriolis",
        label="Use Coriolis",
        description="Enable Coriolis force.",
        group="physics",
        dtype="bool",
        default=True,
    ),
    REMORAParameter(
        key="remora.coriolis_type",
        label="Coriolis Type",
        description="Type of Coriolis parameterization.",
        group="physics",
        dtype="enum",
        default="beta_plane",
        enum_options=["beta_plane", "custom"],
        depends_on={"remora.use_coriolis": True},
    ),
    REMORAParameter(
        key="remora.coriolis_f0",
        label="Coriolis f₀",
        description="Reference Coriolis parameter.",
        group="physics",
        dtype="float",
        default=-8.26e-5,
        units="1/s",
        depends_on={"remora.use_coriolis": True},
    ),
    REMORAParameter(
        key="remora.coriolis_beta",
        label="Coriolis β",
        description="Beta-plane gradient.",
        group="physics",
        dtype="float",
        default=0.0,
        units="1/(m·s)",
        depends_on={"remora.use_coriolis": True},
    ),
    REMORAParameter(
        key="remora.use_gravity",
        label="Use Gravity",
        description="Enable gravitational acceleration.",
        group="physics",
        dtype="bool",
        default=True,
    ),
]

# ---------------------------------------------------------------------------
# Vertical Mixing (PRD §7.4)
# ---------------------------------------------------------------------------

_MIXING_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.vertical_mixing_type",
        label="Mixing Type",
        description="Vertical mixing parameterization.",
        group="mixing",
        dtype="enum",
        default="gls",
        enum_options=["gls", "analytic"],
    ),
    REMORAParameter(
        key="remora.gls_stability_type",
        label="GLS Stability Type",
        description="GLS stability function.",
        group="mixing",
        dtype="enum",
        default="galperin",
        enum_options=["galperin", "kantha_clayson"],
        depends_on={"remora.vertical_mixing_type": "gls"},
    ),
    REMORAParameter(
        key="remora.gls_P",
        label="GLS p",
        description="GLS parameter p.",
        group="mixing",
        dtype="float",
        default=3.0,
        depends_on={"remora.vertical_mixing_type": "gls"},
    ),
    REMORAParameter(
        key="remora.gls_M",
        label="GLS m",
        description="GLS parameter m.",
        group="mixing",
        dtype="float",
        default=1.5,
        depends_on={"remora.vertical_mixing_type": "gls"},
    ),
    REMORAParameter(
        key="remora.gls_N",
        label="GLS n",
        description="GLS parameter n.",
        group="mixing",
        dtype="float",
        default=-1.0,
        depends_on={"remora.vertical_mixing_type": "gls"},
    ),
    REMORAParameter(
        key="remora.Akv_bak",
        label="Background Viscosity",
        description="Background vertical viscosity.",
        group="mixing",
        dtype="float",
        default=1.0e-5,
        min_value=0.0,
        units="m²/s",
    ),
    REMORAParameter(
        key="remora.Akt_bak",
        label="Background Temp Diffusivity",
        description="Background vertical diffusivity for temperature.",
        group="mixing",
        dtype="float",
        default=1.0e-6,
        min_value=0.0,
        units="m²/s",
    ),
    REMORAParameter(
        key="remora.Aks_bak",
        label="Background Salt Diffusivity",
        description="Background vertical diffusivity for salinity.",
        group="mixing",
        dtype="float",
        default=1.0e-6,
        min_value=0.0,
        units="m²/s",
    ),
]

# ---------------------------------------------------------------------------
# Advection Schemes (PRD §7.5)
# ---------------------------------------------------------------------------

_ADVECTION_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.tracer_horizontal_advection_scheme",
        label="Tracer Horiz Advection",
        description="Horizontal advection scheme for tracers.",
        group="advection",
        dtype="enum",
        default="upstream3",
        enum_options=["upstream3", "centered4"],
    ),
    REMORAParameter(
        key="remora.tracer_vertical_advection_scheme",
        label="Tracer Vert Advection",
        description="Vertical advection scheme for tracers.",
        group="advection",
        dtype="enum",
        default="upstream3",
        enum_options=["upstream3", "centered4"],
    ),
]

# ---------------------------------------------------------------------------
# Boundary Conditions (PRD §7.6)
# ---------------------------------------------------------------------------

_BC_TYPES: list[str] = [
    "SlipWall", "NoSlipWall", "Outflow", "Clamped",
    "Chapman", "Flather", "Periodic", "Orlanski", "OrlankiNudg",
]

_BOUNDARY_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key=f"remora.bc.{face}.type",
        label=f"BC {face}",
        description=f"Boundary condition type for the {face} face.",
        group="boundary",
        dtype="enum",
        default="SlipWall",
        required=True,
        enum_options=_BC_TYPES,
    )
    for face in ("xlo", "xhi", "ylo", "yhi", "zlo", "zhi")
]

# ---------------------------------------------------------------------------
# Output Configuration (PRD §7.7)
# ---------------------------------------------------------------------------

_OUTPUT_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="remora.plot_file",
        label="Plot File Prefix",
        description="Prefix for plotfile directory names.",
        group="output",
        dtype="string",
        default="plt",
    ),
    REMORAParameter(
        key="remora.plot_int",
        label="Plot Interval",
        description="Steps between plotfile writes (-1 to disable).",
        group="output",
        dtype="int",
        default=100,
        min_value=-1,
    ),
    REMORAParameter(
        key="remora.plotfile_type",
        label="Plot File Type",
        description="Output format for plotfiles.",
        group="output",
        dtype="enum",
        default="amrex",
        enum_options=["amrex", "netcdf", "hdf5"],
    ),
    REMORAParameter(
        key="remora.plot_vars_3d",
        label="3D Plot Variables",
        description="Which 3D fields to output (space-separated).",
        group="output",
        dtype="string_list",
        default=["salt", "temp", "x_velocity", "y_velocity", "z_velocity"],
    ),
    REMORAParameter(
        key="remora.plot_vars_2d",
        label="2D Plot Variables",
        description="Which 2D fields to output (space-separated).",
        group="output",
        dtype="string_list",
        default=[],
    ),
    REMORAParameter(
        key="remora.check_file",
        label="Checkpoint Prefix",
        description="Prefix for checkpoint directories.",
        group="output",
        dtype="string",
        default="chk",
    ),
    REMORAParameter(
        key="remora.check_int",
        label="Checkpoint Interval",
        description="Steps between checkpoints (negative = wall-clock seconds).",
        group="output",
        dtype="int",
        default=-57600,
    ),
    REMORAParameter(
        key="remora.write_history_file",
        label="Write History File",
        description="Write NetCDF history file.",
        group="output",
        dtype="bool",
        default=False,
        depends_on={"remora.plotfile_type": "netcdf"},
    ),
    REMORAParameter(
        key="remora.sum_interval",
        label="Diagnostic Interval",
        description="Steps between diagnostic summaries.",
        group="output",
        dtype="int",
        default=1,
        min_value=0,
    ),
    REMORAParameter(
        key="remora.v",
        label="Verbosity",
        description="Console output verbosity level.",
        group="output",
        dtype="int",
        default=0,
        min_value=0,
        max_value=2,
    ),
]

# ---------------------------------------------------------------------------
# AMR / Parallelism (PRD §7.8)
# ---------------------------------------------------------------------------

_PARALLEL_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="amr.max_level",
        label="Max AMR Level",
        description="Maximum refinement level (0 = no AMR).",
        group="parallel",
        dtype="int",
        default=0,
        min_value=0,
    ),
    REMORAParameter(
        key="amr.ref_ratio",
        label="Refinement Ratio",
        description="Grid refinement ratio between levels.",
        group="parallel",
        dtype="int",
        default=2,
        min_value=2,
        max_value=4,
    ),
    REMORAParameter(
        key="amr.max_grid_size",
        label="Max Grid Size",
        description="Max cells per grid box (affects load balancing).",
        group="parallel",
        dtype="int",
        default=2048,
        min_value=1,
    ),
    REMORAParameter(
        key="amr.blocking_factor",
        label="Blocking Factor",
        description="Grid cells must be divisible by this value (power of 2).",
        group="parallel",
        dtype="int",
        default=1,
        min_value=1,
    ),
]

# ---------------------------------------------------------------------------
# Restart (PRD §7.9)
# ---------------------------------------------------------------------------

_RESTART_PARAMS: list[REMORAParameter] = [
    REMORAParameter(
        key="amr.restart",
        label="Restart From",
        description="Checkpoint directory to restart from.",
        group="restart",
        dtype="string",
        default="",
    ),
]

# ---------------------------------------------------------------------------
# Assembled schema
# ---------------------------------------------------------------------------

PARAMETER_SCHEMA: dict[str, list[REMORAParameter]] = {
    "domain": _DOMAIN_PARAMS,
    "timing": _TIMING_PARAMS,
    "physics": _PHYSICS_PARAMS,
    "mixing": _MIXING_PARAMS,
    "advection": _ADVECTION_PARAMS,
    "boundary": _BOUNDARY_PARAMS,
    "output": _OUTPUT_PARAMS,
    "parallel": _PARALLEL_PARAMS,
    "restart": _RESTART_PARAMS,
}


def get_parameter(key: str) -> REMORAParameter:
    """Look up a parameter by its key. Raises KeyError if not found."""
    for params in PARAMETER_SCHEMA.values():
        for param in params:
            if param.key == key:
                return param
    raise KeyError(f"Unknown parameter: {key!r}")


def get_group(name: str) -> list[REMORAParameter]:
    """Return all parameters in the given group. Raises KeyError if group unknown."""
    if name not in PARAMETER_SCHEMA:
        raise KeyError(f"Unknown group: {name!r}")
    return PARAMETER_SCHEMA[name]


def get_defaults() -> dict[str, Any]:
    """Return a dict mapping every parameter key to its default value."""
    return {
        param.key: param.default
        for params in PARAMETER_SCHEMA.values()
        for param in params
    }
