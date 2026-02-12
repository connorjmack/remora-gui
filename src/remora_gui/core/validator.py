"""Cross-parameter validation rules for REMORA configurations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ValidationMessage:
    """A single validation finding."""

    level: Literal["error", "warning", "info"]
    message: str
    parameter_keys: list[str] = field(default_factory=list)
    rule_id: str = ""


# ---------------------------------------------------------------------------
# Individual rule implementations
# ---------------------------------------------------------------------------

_FACE_PAIRS: list[tuple[int, str, str]] = [
    (0, "remora.bc.xlo.type", "remora.bc.xhi.type"),
    (1, "remora.bc.ylo.type", "remora.bc.yhi.type"),
    (2, "remora.bc.zlo.type", "remora.bc.zhi.type"),
]

_CORIOLIS_SUB_KEYS = [
    "remora.coriolis_type",
    "remora.coriolis_f0",
    "remora.coriolis_beta",
]


def _r001_fast_dt_divides_dt(params: dict[str, Any]) -> list[ValidationMessage]:
    """fixed_fast_dt should evenly divide fixed_dt."""
    dt = params.get("remora.fixed_dt")
    fast_dt = params.get("remora.fixed_fast_dt")
    if dt is None or fast_dt is None or fast_dt == 0:
        return []
    remainder = dt % fast_dt
    if abs(remainder) > 1e-12 and abs(remainder - fast_dt) > 1e-12:
        return [
            ValidationMessage(
                level="warning",
                message=(
                    f"fixed_fast_dt ({fast_dt}) does not evenly divide "
                    f"fixed_dt ({dt})."
                ),
                parameter_keys=["remora.fixed_dt", "remora.fixed_fast_dt"],
                rule_id="R001",
            )
        ]
    return []


def _r002_periodic_bc_match(params: dict[str, Any]) -> list[ValidationMessage]:
    """Periodic faces must have matching is_periodic flags."""
    is_periodic = params.get("remora.is_periodic")
    if not isinstance(is_periodic, list) or len(is_periodic) < 3:
        return []

    msgs: list[ValidationMessage] = []
    for axis, lo_key, hi_key in _FACE_PAIRS:
        periodic = is_periodic[axis]
        lo_type = params.get(lo_key)
        hi_type = params.get(hi_key)

        if periodic == 1:
            # Periodic axis — face BCs should be absent or "Periodic"
            for face_key, face_type in [(lo_key, lo_type), (hi_key, hi_type)]:
                if face_type is not None and face_type != "Periodic":
                    msgs.append(
                        ValidationMessage(
                            level="error",
                            message=(
                                f"Axis {axis} is periodic but {face_key} is "
                                f"set to {face_type!r} (expected Periodic or unset)."
                            ),
                            parameter_keys=["remora.is_periodic", face_key],
                            rule_id="R002",
                        )
                    )
    return msgs


def _r003_n_cell_positive(params: dict[str, Any]) -> list[ValidationMessage]:
    """n_cell values must all be > 0."""
    n_cell = params.get("remora.n_cell")
    if not isinstance(n_cell, list):
        return []
    for i, val in enumerate(n_cell):
        if val <= 0:
            return [
                ValidationMessage(
                    level="error",
                    message=f"n_cell[{i}] is {val}; all values must be > 0.",
                    parameter_keys=["remora.n_cell"],
                    rule_id="R003",
                )
            ]
    return []


def _r004_prob_hi_gt_lo(params: dict[str, Any]) -> list[ValidationMessage]:
    """prob_hi[i] must be > prob_lo[i] for each dimension."""
    lo = params.get("remora.prob_lo")
    hi = params.get("remora.prob_hi")
    if not isinstance(lo, list) or not isinstance(hi, list):
        return []
    labels = ["x", "y", "z"]
    msgs: list[ValidationMessage] = []
    for i in range(min(len(lo), len(hi))):
        if hi[i] <= lo[i]:
            label = labels[i] if i < len(labels) else str(i)
            msgs.append(
                ValidationMessage(
                    level="error",
                    message=(
                        f"prob_hi[{label}]={hi[i]} must be greater than "
                        f"prob_lo[{label}]={lo[i]}."
                    ),
                    parameter_keys=["remora.prob_lo", "remora.prob_hi"],
                    rule_id="R004",
                )
            )
    return msgs


def _r005_coriolis_unused(params: dict[str, Any]) -> list[ValidationMessage]:
    """If use_coriolis is false, Coriolis sub-params should not be set."""
    if params.get("remora.use_coriolis") is not False:
        return []
    set_keys = [k for k in _CORIOLIS_SUB_KEYS if k in params]
    if set_keys:
        return [
            ValidationMessage(
                level="info",
                message=(
                    "use_coriolis is false but Coriolis sub-parameters are set: "
                    + ", ".join(set_keys)
                    + ". They will be ignored by REMORA."
                ),
                parameter_keys=["remora.use_coriolis", *set_keys],
                rule_id="R005",
            )
        ]
    return []


def _r006_grid_size_ge_blocking(params: dict[str, Any]) -> list[ValidationMessage]:
    """max_grid_size should be >= blocking_factor."""
    grid = params.get("amr.max_grid_size")
    block = params.get("amr.blocking_factor")
    if grid is None or block is None:
        return []
    if grid < block:
        return [
            ValidationMessage(
                level="warning",
                message=(
                    f"max_grid_size ({grid}) is less than "
                    f"blocking_factor ({block})."
                ),
                parameter_keys=["amr.max_grid_size", "amr.blocking_factor"],
                rule_id="R006",
            )
        ]
    return []


def _r007_cfl_estimate(params: dict[str, Any]) -> list[ValidationMessage]:
    """CFL condition estimate: dt * max_velocity / dx < 1.

    Uses a conservative velocity estimate of 2 m/s (typical ocean current).
    """
    dt = params.get("remora.fixed_dt")
    lo = params.get("remora.prob_lo")
    hi = params.get("remora.prob_hi")
    n_cell = params.get("remora.n_cell")

    if dt is None or not isinstance(lo, list) or not isinstance(hi, list):
        return []
    if not isinstance(n_cell, list) or len(n_cell) < 3:
        return []
    if any(n <= 0 for n in n_cell):
        return []

    # Compute minimum dx across all dimensions
    dx_vals = [(hi[i] - lo[i]) / n_cell[i] for i in range(min(len(lo), len(hi), len(n_cell)))]
    nonzero = [abs(d) for d in dx_vals if d != 0]
    dx_min = min(nonzero) if nonzero else 0

    if dx_min == 0:
        return []

    # Conservative velocity estimate for ocean currents
    max_velocity = 2.0  # m/s
    cfl = dt * max_velocity / dx_min

    if cfl >= 1.0:
        return [
            ValidationMessage(
                level="warning",
                message=(
                    f"CFL estimate is {cfl:.2f} (dt={dt}, dx_min={dx_min:.1f}, "
                    f"assumed max velocity={max_velocity} m/s). "
                    f"CFL should be < 1 for stability."
                ),
                parameter_keys=["remora.fixed_dt", "remora.n_cell"],
                rule_id="R007",
            )
        ]
    return []


def _r008_procs_divide_domain(
    params: dict[str, Any], num_procs: int
) -> list[ValidationMessage]:
    """num_procs should evenly divide the total number of grid cells."""
    if num_procs <= 1:
        return []
    n_cell = params.get("remora.n_cell")
    if not isinstance(n_cell, list) or len(n_cell) < 3:
        return []

    total_cells = 1
    for n in n_cell:
        total_cells *= n

    if total_cells % num_procs != 0:
        return [
            ValidationMessage(
                level="warning",
                message=(
                    f"Total grid cells ({total_cells}) is not evenly divisible "
                    f"by num_procs ({num_procs}). This may cause load imbalance."
                ),
                parameter_keys=["remora.n_cell"],
                rule_id="R008",
            )
        ]
    return []


def _r009_n_cell_divisible_by_blocking(params: dict[str, Any]) -> list[ValidationMessage]:
    """n_cell values should be divisible by blocking_factor."""
    n_cell = params.get("remora.n_cell")
    block = params.get("amr.blocking_factor")
    if not isinstance(n_cell, list) or block is None or block <= 0:
        return []

    bad: list[str] = []
    labels = ["x", "y", "z"]
    for i, n in enumerate(n_cell):
        if n % block != 0:
            label = labels[i] if i < len(labels) else str(i)
            bad.append(f"n_cell[{label}]={n}")

    if bad:
        return [
            ValidationMessage(
                level="warning",
                message=(
                    f"{', '.join(bad)} not divisible by blocking_factor ({block})."
                ),
                parameter_keys=["remora.n_cell", "amr.blocking_factor"],
                rule_id="R009",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_RULES = [
    _r001_fast_dt_divides_dt,
    _r002_periodic_bc_match,
    _r003_n_cell_positive,
    _r004_prob_hi_gt_lo,
    _r005_coriolis_unused,
    _r006_grid_size_ge_blocking,
    _r007_cfl_estimate,
    _r009_n_cell_divisible_by_blocking,
]


def validate(params: dict[str, Any], *, num_procs: int = 1) -> list[ValidationMessage]:
    """Run all validation rules against *params* and return findings."""
    messages: list[ValidationMessage] = []
    for rule in _RULES:
        messages.extend(rule(params))
    messages.extend(_r008_procs_divide_domain(params, num_procs))
    return messages
