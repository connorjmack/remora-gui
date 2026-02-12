"""Template library — bundled REMORA example configurations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def list_templates() -> list[dict[str, Any]]:
    """Return metadata for all bundled templates (sorted by name)."""
    templates: list[dict[str, Any]] = []
    for path in sorted(_TEMPLATES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        templates.append({
            "name": data["name"],
            "description": data["description"],
            "category": data.get("category", ""),
            "file": path.name,
        })
    return templates


def load_template(name: str) -> dict[str, Any]:
    """Load a template by filename (e.g. ``"upwelling.json"``) or stem (``"upwelling"``).

    Returns the full template dict including ``name``, ``description``,
    ``category``, and ``parameters``.
    """
    # Accept with or without .json extension
    stem = name.removesuffix(".json")
    path = _TEMPLATES_DIR / f"{stem}.json"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {name!r}")
    return json.loads(path.read_text())  # type: ignore[no-any-return]
