"""Tests for ui/widgets/ — Task 2.4."""

from __future__ import annotations

import pytest

from remora_gui.core.parameter_schema import REMORAParameter
from remora_gui.ui.widgets.collapsible_group import CollapsibleGroupBox
from remora_gui.ui.widgets.enum_combo import EnumComboBox
from remora_gui.ui.widgets.file_picker import FilePickerWidget
from remora_gui.ui.widgets.parameter_widget import ParameterWidget, ScientificSpinBox
from remora_gui.ui.widgets.vector3_widget import Vector3Widget

# ---- Vector3Widget ----


class TestVector3WidgetFloat:
    def test_default_value(self, qtbot):
        w = Vector3Widget(float_mode=True)
        qtbot.addWidget(w)
        assert w.value() == [0.0, 0.0, 0.0]

    def test_set_and_get(self, qtbot):
        w = Vector3Widget(float_mode=True)
        qtbot.addWidget(w)
        w.set_value([1.5, -2.3, 100.0])
        assert w.value() == pytest.approx([1.5, -2.3, 100.0])

    def test_signal_fires(self, qtbot):
        w = Vector3Widget(float_mode=True)
        qtbot.addWidget(w)
        with qtbot.waitSignal(w.value_changed):
            w.set_value([1.0, 2.0, 3.0])


class TestVector3WidgetInt:
    def test_default_value(self, qtbot):
        w = Vector3Widget(float_mode=False)
        qtbot.addWidget(w)
        assert w.value() == [0, 0, 0]

    def test_set_and_get(self, qtbot):
        w = Vector3Widget(float_mode=False)
        qtbot.addWidget(w)
        w.set_value([10, 20, 30])
        assert w.value() == [10, 20, 30]


# ---- EnumComboBox ----


class TestEnumComboBox:
    def test_options_populated(self, qtbot):
        w = EnumComboBox(["alpha", "beta", "gamma"])
        qtbot.addWidget(w)
        assert w.count() == 3

    def test_set_and_get(self, qtbot):
        w = EnumComboBox(["alpha", "beta", "gamma"])
        qtbot.addWidget(w)
        w.set_value("beta")
        assert w.value() == "beta"

    def test_signal_fires(self, qtbot):
        w = EnumComboBox(["alpha", "beta"])
        qtbot.addWidget(w)
        with qtbot.waitSignal(w.enum_value_changed):
            w.set_value("beta")


# ---- FilePickerWidget ----


class TestFilePickerWidget:
    def test_set_and_get(self, qtbot):
        w = FilePickerWidget()
        qtbot.addWidget(w)
        w.set_value("/tmp/test.txt")
        assert w.value() == "/tmp/test.txt"

    def test_signal_fires(self, qtbot):
        w = FilePickerWidget()
        qtbot.addWidget(w)
        with qtbot.waitSignal(w.value_changed):
            w.set_value("/tmp/foo")


# ---- CollapsibleGroupBox ----


class TestCollapsibleGroupBox:
    def test_starts_expanded(self, qtbot):
        w = CollapsibleGroupBox("Test Group")
        qtbot.addWidget(w)
        assert w.isChecked()

    def test_collapse_hides_content(self, qtbot):
        w = CollapsibleGroupBox("Test Group")
        qtbot.addWidget(w)
        w.setChecked(False)
        assert not w.isChecked()


# ---- ScientificSpinBox ----


class TestScientificSpinBox:
    def test_large_value_scientific(self, qtbot):
        box = ScientificSpinBox()
        qtbot.addWidget(box)
        box.setRange(-1e15, 1e15)
        box.setDecimals(8)
        text = box.textFromValue(1.7e-4)
        assert "e" in text or "E" in text

    def test_normal_value_not_scientific(self, qtbot):
        box = ScientificSpinBox()
        qtbot.addWidget(box)
        box.setDecimals(2)
        text = box.textFromValue(42.0)
        assert "e" not in text.lower()

    def test_value_from_text_scientific(self, qtbot):
        box = ScientificSpinBox()
        qtbot.addWidget(box)
        assert box.valueFromText("1.7e-4") == pytest.approx(1.7e-4)


# ---- ParameterWidget ----


def _make_param(**overrides) -> REMORAParameter:
    """Helper to build a REMORAParameter with sensible defaults."""
    defaults = {
        "key": "remora.test",
        "label": "Test",
        "description": "A test parameter",
        "group": "domain",
        "dtype": "int",
        "default": None,
    }
    defaults.update(overrides)
    return REMORAParameter(**defaults)


class TestParameterWidgetInt:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="int", default=10)
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == 10

    def test_signal_fires(self, qtbot):
        p = _make_param(dtype="int", default=0)
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        with qtbot.waitSignal(w.value_changed):
            # Directly manipulate the spin box (not set_value which blocks signals).
            w._input.setValue(42)


class TestParameterWidgetFloat:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="float", default=3.14)
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == pytest.approx(3.14)


class TestParameterWidgetBool:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="bool", default=True)
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() is True

    def test_set_false(self, qtbot):
        p = _make_param(dtype="bool", default=False)
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() is False


class TestParameterWidgetString:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="string", default="hello")
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == "hello"


class TestParameterWidgetEnum:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="enum", default="beta", enum_options=["alpha", "beta", "gamma"])
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == "beta"


class TestParameterWidgetVec3:
    def test_int_vec3(self, qtbot):
        p = _make_param(dtype="int_vec3", default=[10, 20, 30])
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == [10, 20, 30]

    def test_float_vec3(self, qtbot):
        p = _make_param(dtype="float_vec3", default=[1.0, 2.0, 3.0])
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == pytest.approx([1.0, 2.0, 3.0])


class TestParameterWidgetStringList:
    def test_set_and_get(self, qtbot):
        p = _make_param(dtype="string_list", default=["salt", "temp"])
        w = ParameterWidget(p)
        qtbot.addWidget(w)
        assert w.value() == ["salt", "temp"]
