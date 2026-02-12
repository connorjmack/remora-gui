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
]


def validate(params: dict[str, Any]) -> list[ValidationMessage]:
    """Run all validation rules against *params* and return findings."""
    messages: list[ValidationMessage] = []
    for rule in _RULES:
        messages.extend(rule(params))
    return messages
