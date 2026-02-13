"""Parse and write REMORA (AMReX ParmParse) input files."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Any


def _parse_value(raw: str) -> Any:
    """Convert a single whitespace-trimmed value token to a Python type.

    Order of detection: bool → int → float → string.
    """
    if raw == "true":
        return True
    if raw == "false":
        return False
    # Try int (no decimal point, no exponent)
    if re.fullmatch(r"[+-]?\d+", raw):
        return int(raw)
    # Try float (decimal point or scientific notation)
    try:
        return float(raw)
    except ValueError:
        return raw


def _strip_quotes(s: str) -> str:
    """Remove surrounding double quotes from a string, if present."""
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _strip_inline_comment(value_part: str) -> str:
    """Remove an inline ``# comment`` from the value portion of a line.

    Respects quoted strings — a ``#`` inside quotes is not a comment.
    """
    in_quotes = False
    for i, ch in enumerate(value_part):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == '#' and not in_quotes:
            return value_part[:i]
    return value_part


def parse_input_string(text: str) -> OrderedDict[str, Any]:
    """Parse a REMORA input file from a string.

    Returns an :class:`OrderedDict` preserving the parameter order found in
    the text.
    """
    result: OrderedDict[str, Any] = OrderedDict()

    for line in text.splitlines():
        stripped = line.strip()

        # Skip blank lines and full-line comments
        if not stripped or stripped.startswith("#"):
            continue

        # Split on the first '='
        if "=" not in stripped:
            continue
        key_part, value_part = stripped.split("=", 1)
        key = key_part.strip()
        if not key:
            continue

        # Strip inline comment, then trim whitespace
        value_part = _strip_inline_comment(value_part).strip()
        if not value_part:
            result[key] = ""
            continue

        # Tokenise: if the entire value is a single quoted string, treat as
        # one token.  Otherwise split on whitespace.
        if value_part.startswith('"') and value_part.endswith('"') and value_part.count('"') == 2:
            result[key] = _strip_quotes(value_part)
            continue

        tokens = value_part.split()
        tokens = [_strip_quotes(t) for t in tokens]

        if len(tokens) == 1:
            result[key] = _parse_value(tokens[0])
        else:
            result[key] = [_parse_value(t) for t in tokens]

    return result


def parse_input_file(path: str | Path) -> OrderedDict[str, Any]:
    """Parse a REMORA input file from disk.

    Thin wrapper around :func:`parse_input_string`.
    """
    return parse_input_string(Path(path).read_text())


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def _format_value(value: Any) -> str:
    """Format a single Python value back to AMReX ParmParse syntax."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        # Use scientific notation for very small or very large floats,
        # otherwise use default repr (which preserves ".0" for whole floats).
        abs_val = abs(value)
        if value != 0.0 and (abs_val < 1e-3 or abs_val >= 1e7):
            return f"{value:g}"
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return " ".join(_format_value(v) for v in value)
    # String — no quoting needed in the output (REMORA reads unquoted fine)
    return str(value)


_PERIODIC_BC_FACES = {
    0: ("remora.bc.xlo.type", "remora.bc.xhi.type"),
    1: ("remora.bc.ylo.type", "remora.bc.yhi.type"),
    2: ("remora.bc.zlo.type", "remora.bc.zhi.type"),
}


def clean_params_for_remora(params: dict[str, Any]) -> dict[str, Any]:
    """Sanitize parameters before writing for REMORA consumption.

    - Remove BC entries for periodic faces (AMReX aborts otherwise).
    - Remove ``stop_time`` when 0.0 (means "stop immediately", not "no limit").
    """
    result = dict(params)

    # Periodic BC cleanup.
    is_periodic = result.get("remora.is_periodic")
    if isinstance(is_periodic, list):
        for dim, flags in enumerate(is_periodic):
            if dim in _PERIODIC_BC_FACES and flags:
                for key in _PERIODIC_BC_FACES[dim]:
                    result.pop(key, None)

    # stop_time = 0 means "stop at time 0" in AMReX, not "no limit".
    stop_time = result.get("remora.stop_time")
    if stop_time is not None and float(stop_time) == 0.0:
        result.pop("remora.stop_time", None)

    return result


def write_input_string(
    params: dict[str, Any],
    *,
    schema: dict[str, list[Any]] | None = None,
    include_defaults: bool = False,
    header_comment: str | None = None,
) -> str:
    """Serialize a parameter dict to an AMReX ParmParse input-file string.

    Parameters are grouped by their key prefix (e.g. ``remora.*``, ``amr.*``)
    with a blank-line separator and a comment header between groups.

    If *schema* is provided and *include_defaults* is ``False``, parameters
    whose value matches the schema default are omitted.
    """
    # Build a lookup of schema defaults keyed by parameter key.
    default_lookup: dict[str, Any] = {}
    if schema is not None:
        for group_params in schema.values():
            for p in group_params:
                default_lookup[p.key] = p.default  # type: ignore[union-attr]

    # Group keys by prefix (everything before the first dot).
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for key in params:
        prefix = key.split(".")[0]
        groups.setdefault(prefix, []).append(key)

    lines: list[str] = []

    if header_comment is not None:
        for comment_line in header_comment.splitlines():
            lines.append(f"# {comment_line}" if comment_line else "#")
        lines.append("")

    first_group = True
    for prefix, keys in groups.items():
        section_lines: list[str] = []
        for key in keys:
            value = params[key]
            # Skip empty values — AMReX ParmParse rejects "key = " with no value.
            if value == "" or value == [] or value is None:
                continue
            # Optionally skip defaults
            if (
                schema is not None
                and not include_defaults
                and key in default_lookup
                and value == default_lookup[key]
            ):
                continue
            section_lines.append(f"{key} = {_format_value(value)}")

        if not section_lines:
            continue

        if not first_group:
            lines.append("")
        lines.append(f"# {prefix}")
        lines.extend(section_lines)
        first_group = False

    lines.append("")  # trailing newline
    return "\n".join(lines)


def write_input_file(
    params: dict[str, Any],
    path: str | Path,
    *,
    schema: dict[str, list[Any]] | None = None,
    include_defaults: bool = False,
    header_comment: str | None = None,
) -> None:
    """Write a parameter dict to an AMReX ParmParse input file on disk."""
    Path(path).write_text(
        write_input_string(
            params,
            schema=schema,
            include_defaults=include_defaults,
            header_comment=header_comment,
        )
    )
