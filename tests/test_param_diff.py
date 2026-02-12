"""Tests for parameter diff logic."""

from __future__ import annotations

from remora_gui.core.param_diff import DiffEntry, diff_parameters


class TestDiffParameters:
    """Test diff_parameters returns correct DiffEntry results."""

    def test_identical_params_returns_empty(self) -> None:
        params = {"remora.fixed_dt": 300.0, "remora.n_cell": [80, 80, 16]}
        result = diff_parameters(params, params)
        assert result == []

    def test_changed_scalar(self) -> None:
        a = {"remora.fixed_dt": 300.0}
        b = {"remora.fixed_dt": 600.0}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0] == DiffEntry(
            key="remora.fixed_dt", kind="changed", value_a=300.0, value_b=600.0
        )

    def test_changed_list(self) -> None:
        a = {"remora.n_cell": [80, 80, 16]}
        b = {"remora.n_cell": [80, 80, 32]}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0].kind == "changed"
        assert result[0].value_a == [80, 80, 16]
        assert result[0].value_b == [80, 80, 32]

    def test_added_in_b(self) -> None:
        a = {"remora.fixed_dt": 300.0}
        b = {"remora.fixed_dt": 300.0, "remora.stop_time": 1000.0}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0] == DiffEntry(
            key="remora.stop_time", kind="added", value_a=None, value_b=1000.0
        )

    def test_removed_in_b(self) -> None:
        a = {"remora.fixed_dt": 300.0, "remora.stop_time": 1000.0}
        b = {"remora.fixed_dt": 300.0}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0] == DiffEntry(
            key="remora.stop_time", kind="removed", value_a=1000.0, value_b=None
        )

    def test_multiple_diffs_sorted_by_key(self) -> None:
        a = {"b.key": 1, "a.key": 2, "c.key": 3}
        b = {"b.key": 1, "a.key": 9, "c.key": 7}
        result = diff_parameters(a, b)
        assert len(result) == 2
        assert result[0].key == "a.key"
        assert result[1].key == "c.key"

    def test_empty_dicts(self) -> None:
        assert diff_parameters({}, {}) == []

    def test_all_new_in_b(self) -> None:
        result = diff_parameters({}, {"x": 1, "y": 2})
        assert len(result) == 2
        assert all(e.kind == "added" for e in result)

    def test_all_removed_in_b(self) -> None:
        result = diff_parameters({"x": 1, "y": 2}, {})
        assert len(result) == 2
        assert all(e.kind == "removed" for e in result)

    def test_bool_change(self) -> None:
        a = {"remora.use_coriolis": True}
        b = {"remora.use_coriolis": False}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0].kind == "changed"
        assert result[0].value_a is True
        assert result[0].value_b is False

    def test_int_float_equal_not_changed(self) -> None:
        a = {"x": 1}
        b = {"x": 1.0}
        # Python treats 1 == 1.0, so no diff reported
        result = diff_parameters(a, b)
        assert result == []

    def test_string_change(self) -> None:
        a = {"remora.bc.xlo.type": "SlipWall"}
        b = {"remora.bc.xlo.type": "NoSlipWall"}
        result = diff_parameters(a, b)
        assert len(result) == 1
        assert result[0].kind == "changed"
