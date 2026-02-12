"""Tests for core/validator.py — Task 1.5."""

from __future__ import annotations

from remora_gui.core.parameter_schema import get_defaults
from remora_gui.core.validator import validate


def _defaults(**overrides: object) -> dict[str, object]:
    """Return schema defaults with optional overrides."""
    d = get_defaults()
    d.update(overrides)
    return d


# ---------------------------------------------------------------------------
# Valid config → no errors
# ---------------------------------------------------------------------------


class TestValidDefaults:
    def test_defaults_produce_no_errors(self) -> None:
        # Default schema has is_periodic=[1,0,0] (x-axis periodic),
        # so remove x-face BC types to avoid R002 conflict.
        params = _defaults()
        params.pop("remora.bc.xlo.type", None)
        params.pop("remora.bc.xhi.type", None)
        msgs = validate(params)
        errors = [m for m in msgs if m.level == "error"]
        assert errors == [], [m.message for m in errors]


# ---------------------------------------------------------------------------
# R001 — fixed_fast_dt should evenly divide fixed_dt
# ---------------------------------------------------------------------------


class TestR001:
    def test_clean_division_no_warning(self) -> None:
        msgs = validate(_defaults(**{"remora.fixed_dt": 300.0, "remora.fixed_fast_dt": 10.0}))
        assert all(m.rule_id != "R001" for m in msgs)

    def test_uneven_division_warns(self) -> None:
        msgs = validate(_defaults(**{"remora.fixed_dt": 300.0, "remora.fixed_fast_dt": 7.0}))
        r001 = [m for m in msgs if m.rule_id == "R001"]
        assert len(r001) == 1
        assert r001[0].level == "warning"


# ---------------------------------------------------------------------------
# R002 — Periodic faces must match is_periodic flags
# ---------------------------------------------------------------------------


class TestR002:
    def test_periodic_without_bc_no_error(self) -> None:
        """is_periodic=[1,0,0] with no xlo/xhi BC set → fine."""
        params = _defaults()
        # Remove x-face BCs so they don't conflict
        params.pop("remora.bc.xlo.type", None)
        params.pop("remora.bc.xhi.type", None)
        msgs = validate(params)
        assert all(m.rule_id != "R002" for m in msgs)

    def test_periodic_with_non_periodic_bc_errors(self) -> None:
        params = _defaults(**{
            "remora.is_periodic": [1, 0, 0],
            "remora.bc.xlo.type": "SlipWall",
        })
        r002 = [m for m in validate(params) if m.rule_id == "R002"]
        assert len(r002) >= 1
        assert r002[0].level == "error"

    def test_non_periodic_axis_any_bc_ok(self) -> None:
        params = _defaults(**{
            "remora.is_periodic": [0, 0, 0],
            "remora.bc.xlo.type": "SlipWall",
            "remora.bc.xhi.type": "Outflow",
        })
        msgs = validate(params)
        assert all(m.rule_id != "R002" for m in msgs)


# ---------------------------------------------------------------------------
# R003 — n_cell values must all be > 0
# ---------------------------------------------------------------------------


class TestR003:
    def test_positive_cells_ok(self) -> None:
        msgs = validate(_defaults(**{"remora.n_cell": [41, 80, 16]}))
        assert all(m.rule_id != "R003" for m in msgs)

    def test_zero_cell_errors(self) -> None:
        msgs = validate(_defaults(**{"remora.n_cell": [0, 80, 16]}))
        r003 = [m for m in msgs if m.rule_id == "R003"]
        assert len(r003) == 1
        assert r003[0].level == "error"

    def test_negative_cell_errors(self) -> None:
        msgs = validate(_defaults(**{"remora.n_cell": [41, -1, 16]}))
        r003 = [m for m in msgs if m.rule_id == "R003"]
        assert len(r003) == 1
        assert r003[0].level == "error"


# ---------------------------------------------------------------------------
# R004 — prob_hi[i] must be > prob_lo[i]
# ---------------------------------------------------------------------------


class TestR004:
    def test_valid_bounds_ok(self) -> None:
        msgs = validate(_defaults(**{
            "remora.prob_lo": [0.0, 0.0, -150.0],
            "remora.prob_hi": [41000.0, 80000.0, 0.0],
        }))
        assert all(m.rule_id != "R004" for m in msgs)

    def test_equal_bounds_errors(self) -> None:
        msgs = validate(_defaults(**{
            "remora.prob_lo": [0.0, 0.0, 0.0],
            "remora.prob_hi": [0.0, 0.0, 0.0],
        }))
        r004 = [m for m in msgs if m.rule_id == "R004"]
        assert len(r004) == 3  # one per dimension
        assert all(m.level == "error" for m in r004)

    def test_inverted_single_axis_errors(self) -> None:
        msgs = validate(_defaults(**{
            "remora.prob_lo": [0.0, 0.0, 0.0],
            "remora.prob_hi": [100.0, 100.0, -50.0],
        }))
        r004 = [m for m in msgs if m.rule_id == "R004"]
        assert len(r004) == 1
        assert "z" in r004[0].message


# ---------------------------------------------------------------------------
# R005 — Coriolis sub-params when use_coriolis=false
# ---------------------------------------------------------------------------


class TestR005:
    def test_coriolis_enabled_no_info(self) -> None:
        msgs = validate(_defaults(**{"remora.use_coriolis": True}))
        assert all(m.rule_id != "R005" for m in msgs)

    def test_coriolis_disabled_with_sub_params_info(self) -> None:
        params = _defaults(**{"remora.use_coriolis": False})
        # Defaults include coriolis sub-params from schema
        msgs = validate(params)
        r005 = [m for m in msgs if m.rule_id == "R005"]
        assert len(r005) == 1
        assert r005[0].level == "info"


# ---------------------------------------------------------------------------
# R006 — max_grid_size >= blocking_factor
# ---------------------------------------------------------------------------


class TestR006:
    def test_grid_ge_blocking_ok(self) -> None:
        msgs = validate(_defaults(**{
            "amr.max_grid_size": 2048,
            "amr.blocking_factor": 1,
        }))
        assert all(m.rule_id != "R006" for m in msgs)

    def test_grid_lt_blocking_warns(self) -> None:
        msgs = validate(_defaults(**{
            "amr.max_grid_size": 4,
            "amr.blocking_factor": 16,
        }))
        r006 = [m for m in msgs if m.rule_id == "R006"]
        assert len(r006) == 1
        assert r006[0].level == "warning"
