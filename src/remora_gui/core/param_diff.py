"""Parameter diff logic for comparing two simulation configurations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class DiffEntry:
    """A single difference between two parameter sets."""

    key: str
    kind: Literal["added", "removed", "changed"]
    value_a: Any = None
    value_b: Any = None


def diff_parameters(
    params_a: dict[str, Any],
    params_b: dict[str, Any],
) -> list[DiffEntry]:
    """Compare two parameter dicts and return a sorted list of differences.

    - ``added``: key exists in *params_b* but not *params_a*
    - ``removed``: key exists in *params_a* but not *params_b*
    - ``changed``: key exists in both but values differ
    """
    diffs: list[DiffEntry] = []
    all_keys = set(params_a) | set(params_b)

    for key in all_keys:
        in_a = key in params_a
        in_b = key in params_b

        if in_a and not in_b:
            diffs.append(DiffEntry(key=key, kind="removed", value_a=params_a[key]))
        elif in_b and not in_a:
            diffs.append(DiffEntry(key=key, kind="added", value_b=params_b[key]))
        elif params_a[key] != params_b[key]:
            diffs.append(
                DiffEntry(
                    key=key, kind="changed", value_a=params_a[key], value_b=params_b[key]
                )
            )

    diffs.sort(key=lambda d: d.key)
    return diffs
