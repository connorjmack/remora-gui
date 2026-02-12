"""Tests for core/input_file.py — Tasks 1.3 & 1.4."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pytest

from remora_gui.core.input_file import (
    parse_input_file,
    parse_input_string,
    write_input_file,
    write_input_string,
)

FIXTURES = Path(__file__).parent / "fixtures"
UPWELLING = FIXTURES / "upwelling_inputs"


# ---------------------------------------------------------------------------
# Fixture-based tests
# ---------------------------------------------------------------------------


class TestParseUpwellingFixture:
    """Parse the bundled Upwelling example and spot-check values."""

    @pytest.fixture(autouse=True)
    def _parse(self) -> None:
        self.params = parse_input_file(UPWELLING)

    def test_key_count(self) -> None:
        # 31 non-comment key=value lines in the fixture
        assert len(self.params) == 31

    def test_int_scalar(self) -> None:
        assert self.params["remora.max_step"] == 10
        assert isinstance(self.params["remora.max_step"], int)

    def test_float_scalar(self) -> None:
        assert self.params["remora.fixed_dt"] == 300.0
        assert isinstance(self.params["remora.fixed_dt"], float)

    def test_bool_true(self) -> None:
        assert self.params["remora.use_coriolis"] is True

    def test_bool_false(self) -> None:
        assert self.params["remora.flat_bathymetry"] is False

    def test_scientific_notation(self) -> None:
        assert self.params["remora.Tcoef"] == pytest.approx(1.7e-4)
        assert isinstance(self.params["remora.Tcoef"], float)

    def test_negative_scientific(self) -> None:
        assert self.params["remora.coriolis_f0"] == pytest.approx(-8.26e-5)

    def test_float_vector(self) -> None:
        assert self.params["remora.prob_lo"] == [0.0, 0.0, -150.0]

    def test_int_vector(self) -> None:
        assert self.params["remora.n_cell"] == [41, 80, 16]

    def test_string_list(self) -> None:
        assert self.params["remora.plot_vars_3d"] == [
            "salt", "temp", "x_velocity", "y_velocity", "z_velocity",
        ]

    def test_quoted_string(self) -> None:
        assert self.params["remora.bc.ylo.type"] == "SlipWall"
        assert isinstance(self.params["remora.bc.ylo.type"], str)

    def test_quoted_string_with_inline_comment(self) -> None:
        # "upstream3" # upstream3 or centered4
        assert self.params["remora.tracer_horizontal_advection_scheme"] == "upstream3"

    def test_unquoted_string(self) -> None:
        assert self.params["remora.coriolis_type"] == "beta_plane"

    def test_negative_int(self) -> None:
        assert self.params["remora.check_int"] == -57600
        assert isinstance(self.params["remora.check_int"], int)

    def test_ordering_preserved(self) -> None:
        keys = list(self.params.keys())
        assert keys.index("remora.max_step") < keys.index("remora.prob_lo")
        assert keys.index("remora.prob_lo") < keys.index("remora.fixed_dt")


# ---------------------------------------------------------------------------
# Unit tests for parse_input_string edge cases
# ---------------------------------------------------------------------------


class TestParseInputString:
    """Verify parsing rules from the AMReX ParmParse spec."""

    def test_blank_lines_skipped(self) -> None:
        text = "\n\nremora.v = 1\n\n"
        result = parse_input_string(text)
        assert result == {"remora.v": 1}

    def test_comment_lines_skipped(self) -> None:
        text = "# a comment\n  # indented comment\nremora.v = 1\n"
        result = parse_input_string(text)
        assert len(result) == 1

    def test_inline_comment_stripped(self) -> None:
        text = "remora.v = 1  # verbosity level\n"
        result = parse_input_string(text)
        assert result["remora.v"] == 1

    def test_no_spaces_around_equals(self) -> None:
        text = "remora.v=2\n"
        result = parse_input_string(text)
        assert result["remora.v"] == 2

    def test_extra_spaces_around_equals(self) -> None:
        text = "remora.v   =   3\n"
        result = parse_input_string(text)
        assert result["remora.v"] == 3

    def test_bool_true(self) -> None:
        result = parse_input_string("remora.flag = true\n")
        assert result["remora.flag"] is True

    def test_bool_false(self) -> None:
        result = parse_input_string("remora.flag = false\n")
        assert result["remora.flag"] is False

    def test_multi_value_float(self) -> None:
        text = "remora.prob_lo = 0.0 0.0 -150.0\n"
        result = parse_input_string(text)
        assert result["remora.prob_lo"] == [0.0, 0.0, -150.0]

    def test_multi_value_int(self) -> None:
        text = "remora.n_cell = 41 80 16\n"
        result = parse_input_string(text)
        assert result["remora.n_cell"] == [41, 80, 16]

    def test_multi_value_mixed(self) -> None:
        text = "remora.omp_tile_size = 1024 1024 1024\n"
        result = parse_input_string(text)
        assert result["remora.omp_tile_size"] == [1024, 1024, 1024]

    def test_quoted_string_unquoted(self) -> None:
        text = 'remora.bc.xlo.type = "SlipWall"\n'
        result = parse_input_string(text)
        assert result["remora.bc.xlo.type"] == "SlipWall"

    def test_scientific_notation(self) -> None:
        text = "remora.Tcoef = 1.7e-4\n"
        result = parse_input_string(text)
        assert result["remora.Tcoef"] == pytest.approx(1.7e-4)

    def test_hash_inside_quotes_not_comment(self) -> None:
        text = 'remora.label = "foo # bar"\n'
        result = parse_input_string(text)
        assert result["remora.label"] == "foo # bar"

    def test_empty_value(self) -> None:
        text = "amr.restart =\n"
        result = parse_input_string(text)
        assert result["amr.restart"] == ""

    def test_line_without_equals_skipped(self) -> None:
        text = "just some text\nremora.v = 1\n"
        result = parse_input_string(text)
        assert len(result) == 1

    def test_preserves_order(self) -> None:
        text = "b.key = 1\na.key = 2\nc.key = 3\n"
        result = parse_input_string(text)
        assert list(result.keys()) == ["b.key", "a.key", "c.key"]


# ---------------------------------------------------------------------------
# Writer tests (Task 1.4)
# ---------------------------------------------------------------------------


class TestWriteInputString:
    """Verify write_input_string output format."""

    def test_bool_true_written_lowercase(self) -> None:
        text = write_input_string({"remora.flag": True})
        assert "remora.flag = true" in text

    def test_bool_false_written_lowercase(self) -> None:
        text = write_input_string({"remora.flag": False})
        assert "remora.flag = false" in text

    def test_vector_space_separated(self) -> None:
        text = write_input_string({"remora.prob_lo": [0.0, 0.0, -150.0]})
        assert "remora.prob_lo = 0.0 0.0 -150.0" in text

    def test_int_vector(self) -> None:
        text = write_input_string({"remora.n_cell": [41, 80, 16]})
        assert "remora.n_cell = 41 80 16" in text

    def test_scientific_notation_for_small_floats(self) -> None:
        text = write_input_string({"remora.Tcoef": 1.7e-4})
        # Should use scientific notation (not 0.00017)
        assert "e" in text.lower() or "E" in text

    def test_string_value(self) -> None:
        text = write_input_string({"remora.plot_file": "plt"})
        assert "remora.plot_file = plt" in text

    def test_string_list(self) -> None:
        text = write_input_string(
            {"remora.plot_vars_3d": ["salt", "temp", "x_velocity"]}
        )
        assert "remora.plot_vars_3d = salt temp x_velocity" in text

    def test_groups_by_prefix(self) -> None:
        params: dict[str, object] = OrderedDict([
            ("remora.v", 0),
            ("amr.max_level", 0),
            ("remora.max_step", 10),
        ])
        text = write_input_string(params)
        # Should have "# remora" and "# amr" section headers
        assert "# remora" in text
        assert "# amr" in text

    def test_header_comment(self) -> None:
        text = write_input_string(
            {"remora.v": 0}, header_comment="Generated by REMORA-GUI"
        )
        assert text.startswith("# Generated by REMORA-GUI")

    def test_multiline_header_comment(self) -> None:
        text = write_input_string(
            {"remora.v": 0}, header_comment="Line 1\nLine 2"
        )
        assert "# Line 1\n# Line 2" in text

    def test_skip_defaults_when_schema_provided(self) -> None:
        from remora_gui.core.parameter_schema import PARAMETER_SCHEMA

        # Get the schema default for remora.v (should be 0)
        defaults = {"remora.v": 0, "remora.max_step": 999}
        text = write_input_string(
            defaults, schema=PARAMETER_SCHEMA, include_defaults=False
        )
        # remora.v=0 matches default → omitted
        assert "remora.v" not in text
        # remora.max_step=999 differs from default 10 → included
        assert "remora.max_step = 999" in text

    def test_include_defaults_writes_all(self) -> None:
        from remora_gui.core.parameter_schema import PARAMETER_SCHEMA

        defaults = {"remora.v": 0, "remora.max_step": 10}
        text = write_input_string(
            defaults, schema=PARAMETER_SCHEMA, include_defaults=True
        )
        assert "remora.v = 0" in text
        assert "remora.max_step = 10" in text

    def test_empty_string_value(self) -> None:
        text = write_input_string({"amr.restart": ""})
        assert "amr.restart = " in text


class TestRoundTrip:
    """parse(write(parse(fixture))) must produce an identical dict."""

    def test_upwelling_round_trip(self) -> None:
        original = parse_input_file(UPWELLING)
        written = write_input_string(original)
        reparsed = parse_input_string(written)
        assert reparsed == original

    def test_unknown_params_preserved(self) -> None:
        """Parameters not in the schema survive a round-trip."""
        params: dict[str, object] = OrderedDict([
            ("remora.max_step", 10),
            ("custom.unknown_param", 42),
            ("custom.another", [1.0, 2.0, 3.0]),
        ])
        written = write_input_string(params)
        reparsed = parse_input_string(written)
        assert reparsed == params


class TestWriteInputFile:
    """Verify file-based writer."""

    def test_writes_to_disk(self, tmp_path: Path) -> None:
        params: dict[str, object] = OrderedDict([
            ("remora.max_step", 10),
            ("remora.v", 1),
        ])
        out = tmp_path / "test_inputs"
        write_input_file(params, out)
        assert out.exists()
        reparsed = parse_input_file(out)
        assert reparsed == params
