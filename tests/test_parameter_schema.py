"""Tests for core/parameter_schema.py — Tasks 1.1 & 1.2."""

from __future__ import annotations

import pytest

from remora_gui.core.parameter_schema import (
    PARAMETER_GROUPS,
    PARAMETER_SCHEMA,
    REMORAParameter,
    get_defaults,
    get_group,
    get_parameter,
)

# All valid dtype literals (must match the Literal union in REMORAParameter).
VALID_DTYPES = {
    "int", "float", "bool", "string", "enum",
    "int_vec3", "float_vec3", "string_list",
}

# Collect every parameter once for parametrized tests.
ALL_PARAMS: list[REMORAParameter] = [
    p for group in PARAMETER_SCHEMA.values() for p in group
]

# ---------------------------------------------------------------------------
# REMORAParameter dataclass
# ---------------------------------------------------------------------------

SAMPLE_PARAM = REMORAParameter(
    key="remora.fixed_dt",
    label="Time Step (dt)",
    description="Fixed time step size for the simulation.",
    group="timing",
    dtype="float",
    default=300.0,
    required=True,
    min_value=0.0,
    max_value=None,
    units="seconds",
)


class TestREMORAParameter:
    """Verify the dataclass can be instantiated and fields are accessible."""

    def test_instantiation(self) -> None:
        assert SAMPLE_PARAM.key == "remora.fixed_dt"
        assert SAMPLE_PARAM.label == "Time Step (dt)"
        assert SAMPLE_PARAM.dtype == "float"
        assert SAMPLE_PARAM.default == 300.0
        assert SAMPLE_PARAM.required is True
        assert SAMPLE_PARAM.min_value == 0.0
        assert SAMPLE_PARAM.max_value is None
        assert SAMPLE_PARAM.units == "seconds"
        assert SAMPLE_PARAM.reference_url is None

    def test_optional_fields_default_to_none(self) -> None:
        minimal = REMORAParameter(
            key="test.param",
            label="Test",
            description="A test parameter.",
            group="domain",
            dtype="int",
            default=0,
        )
        assert minimal.min_value is None
        assert minimal.max_value is None
        assert minimal.enum_options is None
        assert minimal.depends_on is None
        assert minimal.units is None
        assert minimal.reference_url is None
        assert minimal.required is False

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            SAMPLE_PARAM.key = "something.else"  # type: ignore[misc]

    def test_enum_parameter(self) -> None:
        param = REMORAParameter(
            key="remora.vertical_mixing_type",
            label="Vertical Mixing",
            description="Vertical mixing closure.",
            group="mixing",
            dtype="enum",
            default="gls",
            enum_options=["gls", "kpp", "none"],
        )
        assert param.enum_options == ["gls", "kpp", "none"]

    def test_depends_on(self) -> None:
        param = REMORAParameter(
            key="remora.coriolis_f0",
            label="Coriolis f0",
            description="Base Coriolis parameter.",
            group="physics",
            dtype="float",
            default=0.0,
            depends_on={"remora.use_coriolis": True},
        )
        assert param.depends_on == {"remora.use_coriolis": True}

    def test_vector_dtype(self) -> None:
        param = REMORAParameter(
            key="geometry.prob_lo",
            label="Domain Lower Corner",
            description="Lower corner of the simulation domain.",
            group="domain",
            dtype="float_vec3",
            default=[0.0, 0.0, -150.0],
            units="m",
        )
        assert param.dtype == "float_vec3"
        assert param.default == [0.0, 0.0, -150.0]


# ---------------------------------------------------------------------------
# PARAMETER_GROUPS
# ---------------------------------------------------------------------------


class TestParameterGroups:
    """Verify the ordered group list."""

    def test_expected_groups(self) -> None:
        expected = [
            "domain", "timing", "physics", "mixing", "advection",
            "boundary", "output", "parallel", "restart",
        ]
        assert expected == PARAMETER_GROUPS

    def test_no_duplicates(self) -> None:
        assert len(PARAMETER_GROUPS) == len(set(PARAMETER_GROUPS))

    def test_schema_keys_match_groups(self) -> None:
        assert set(PARAMETER_SCHEMA.keys()) == set(PARAMETER_GROUPS)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    """Test get_parameter, get_group, get_defaults."""

    def test_get_parameter_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown parameter"):
            get_parameter("nonexistent.key")

    def test_get_group_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown group"):
            get_group("nonexistent_group")

    def test_get_group_returns_list(self) -> None:
        for group in PARAMETER_GROUPS:
            result = get_group(group)
            assert isinstance(result, list)

    def test_get_defaults_returns_dict(self) -> None:
        result = get_defaults()
        assert isinstance(result, dict)

    def test_get_parameter_finds_known_key(self) -> None:
        param = get_parameter("remora.fixed_dt")
        assert param.key == "remora.fixed_dt"
        assert param.group == "timing"

    def test_get_defaults_count(self) -> None:
        defaults = get_defaults()
        assert len(defaults) == len(ALL_PARAMS)


# ---------------------------------------------------------------------------
# Schema population validation (Task 1.2)
# ---------------------------------------------------------------------------


class TestSchemaPopulation:
    """Validate the fully-populated PARAMETER_SCHEMA."""

    def test_every_group_has_at_least_one_parameter(self) -> None:
        for group in PARAMETER_GROUPS:
            assert len(PARAMETER_SCHEMA[group]) >= 1, f"Group {group!r} is empty"

    def test_all_dtypes_are_valid(self) -> None:
        for param in ALL_PARAMS:
            assert param.dtype in VALID_DTYPES, (
                f"{param.key}: dtype {param.dtype!r} not in {VALID_DTYPES}"
            )

    def test_no_duplicate_keys(self) -> None:
        keys = [p.key for p in ALL_PARAMS]
        assert len(keys) == len(set(keys)), (
            f"Duplicate keys: {[k for k in keys if keys.count(k) > 1]}"
        )

    def test_param_group_field_matches_schema_group(self) -> None:
        """Each parameter's .group field must match the group it lives in."""
        for group_name, params in PARAMETER_SCHEMA.items():
            for param in params:
                assert param.group == group_name, (
                    f"{param.key}: .group={param.group!r} but in schema group {group_name!r}"
                )

    def test_defaults_within_min_max(self) -> None:
        """Numeric defaults must satisfy declared min/max constraints."""
        for param in ALL_PARAMS:
            if param.default is None:
                continue
            if param.min_value is not None and isinstance(param.default, (int, float)):
                assert param.default >= param.min_value, (
                    f"{param.key}: default {param.default} < min {param.min_value}"
                )
            if param.max_value is not None and isinstance(param.default, (int, float)):
                assert param.default <= param.max_value, (
                    f"{param.key}: default {param.default} > max {param.max_value}"
                )

    def test_enum_params_have_options(self) -> None:
        """Every enum parameter must declare at least two options."""
        for param in ALL_PARAMS:
            if param.dtype == "enum":
                assert param.enum_options is not None and len(param.enum_options) >= 2, (
                    f"{param.key}: enum dtype but missing/empty enum_options"
                )

    def test_enum_default_in_options(self) -> None:
        """Every enum default must be one of its declared options."""
        for param in ALL_PARAMS:
            if param.dtype == "enum" and param.enum_options is not None:
                assert param.default in param.enum_options, (
                    f"{param.key}: default {param.default!r} not in {param.enum_options}"
                )

    def test_depends_on_keys_exist_in_schema(self) -> None:
        """Every key referenced in depends_on must exist in the schema."""
        all_keys = {p.key for p in ALL_PARAMS}
        for param in ALL_PARAMS:
            if param.depends_on is not None:
                for dep_key in param.depends_on:
                    assert dep_key in all_keys, (
                        f"{param.key}: depends_on references unknown key {dep_key!r}"
                    )

    def test_expected_group_sizes(self) -> None:
        """Spot-check expected parameter counts per group."""
        expected = {
            "domain": 5,
            "timing": 4,
            "physics": 12,
            "mixing": 8,
            "advection": 2,
            "boundary": 6,
            "output": 9,
            "parallel": 4,
            "restart": 1,
        }
        for group, count in expected.items():
            assert len(PARAMETER_SCHEMA[group]) == count, (
                f"Group {group!r}: expected {count}, got {len(PARAMETER_SCHEMA[group])}"
            )
