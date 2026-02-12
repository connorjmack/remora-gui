"""Tests for core/templates.py — Task 1.9."""

from __future__ import annotations

import pytest

from remora_gui.core.parameter_schema import PARAMETER_SCHEMA
from remora_gui.core.templates import list_templates, load_template

# All known schema keys for validation.
ALL_SCHEMA_KEYS = {
    p.key for group in PARAMETER_SCHEMA.values() for p in group
}

REQUIRED_META_KEYS = {"name", "description", "category", "parameters"}


class TestListTemplates:
    def test_returns_non_empty(self) -> None:
        templates = list_templates()
        assert len(templates) >= 5

    def test_each_has_required_fields(self) -> None:
        for t in list_templates():
            assert "name" in t
            assert "description" in t
            assert "file" in t

    def test_sorted_by_name(self) -> None:
        names = [t["name"] for t in list_templates()]
        assert names == sorted(names)


class TestLoadTemplate:
    def test_load_by_stem(self) -> None:
        t = load_template("upwelling")
        assert t["name"] == "Upwelling"

    def test_load_by_filename(self) -> None:
        t = load_template("upwelling.json")
        assert t["name"] == "Upwelling"

    def test_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent")

    def test_all_templates_have_required_keys(self) -> None:
        for meta in list_templates():
            t = load_template(meta["file"])
            missing = REQUIRED_META_KEYS - set(t.keys())
            assert not missing, f"{meta['file']} missing keys: {missing}"

    def test_all_templates_parse_without_error(self) -> None:
        for meta in list_templates():
            t = load_template(meta["file"])
            assert isinstance(t["parameters"], dict)
            assert len(t["parameters"]) > 0 or meta["file"] == "blank.json"


class TestTemplateParameterKeys:
    """Every parameter key in a template should exist in the schema
    (warns about unknown keys that would be passed through)."""

    def test_known_keys(self) -> None:
        for meta in list_templates():
            t = load_template(meta["file"])
            for key in t["parameters"]:
                assert key in ALL_SCHEMA_KEYS, (
                    f"Template {meta['file']}: unknown parameter key {key!r}"
                )
