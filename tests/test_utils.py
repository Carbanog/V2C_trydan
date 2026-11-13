"""Tests for defensive charger value conversion."""

from __future__ import annotations

import pytest

from custom_components.v2c_trydan.utils import (
    cable_connected_from_charge_state,
    validate_intensity,
    value_as_bool,
    value_as_float,
    value_as_int,
)


@pytest.mark.parametrize(
    "key,value,data",
    [
        ("MinIntensity", 16, {"MaxIntensity": 15}),
        ("MaxIntensity", 6, {"MinIntensity": 7}),
        ("Intensity", 16, {"MinIntensity": 6, "MaxIntensity": 15}),
        ("Intensity", 6, {"MinIntensity": 7, "MaxIntensity": 15}),
        ("MinIntensity", 6, {}),
        ("MaxIntensity", 15, {"MinIntensity": "invalid"}),
        ("Intensity", True, {"MinIntensity": 6, "MaxIntensity": 15}),
        ("Intensity", 6.5, {"MinIntensity": 6, "MaxIntensity": 15}),
        ("Intensity", 33, {"MinIntensity": 6, "MaxIntensity": 32}),
    ],
)
def test_invalid_intensity_never_bypasses_charger_limits(key, value, data):
    with pytest.raises(ValueError):
        validate_intensity(key, value, data)


@pytest.mark.parametrize(
    "key,value", [("MinIntensity", 15), ("MaxIntensity", 6), ("Intensity", 15)]
)
def test_intensity_limit_equality_is_allowed(key, value):
    validate_intensity(key, value, {"MinIntensity": 6, "MaxIntensity": 15})


def test_only_explicit_cable_states_establish_connection() -> None:
    """Fault and unsupported states must not trigger a false unplug event."""
    assert cable_connected_from_charge_state(0) is False
    assert cable_connected_from_charge_state("1") is True
    assert cable_connected_from_charge_state(2) is True
    for value in (3, 4, 5, 6, 99, None, "invalid", True, 1.5):
        assert cable_connected_from_charge_state(value) is None


def test_value_as_bool_handles_numeric_strings() -> None:
    """Textual zero and one map to the intended switch states."""
    assert value_as_bool("0") is False
    assert value_as_bool("1") is True
    assert value_as_bool("invalid") is None


@pytest.mark.parametrize("value", [2, -1, 0.5, float("nan"), float("inf"), "2"])
def test_value_as_bool_rejects_non_binary_flags(value):
    assert value_as_bool(value) is None


@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0, True, False, "on", "off"])
def test_value_as_bool_preserves_valid_flags(value):
    assert value_as_bool(value) is (value in (1, "on"))


@pytest.mark.parametrize("value", [1.9, -1.9, "1.9", float("nan")])
def test_value_as_int_never_truncates_invalid_states(value):
    assert value_as_int(value) is None


def test_numeric_conversion_rejects_bool_and_invalid_values() -> None:
    """Invalid numeric values remain unknown instead of being fabricated."""
    assert value_as_int("16") == 16
    assert value_as_float("16.5") == 16.5
    assert value_as_int(True) is None
    assert value_as_float("invalid") is None


def test_numeric_conversion_rejects_non_finite_values() -> None:
    """NaN and infinity must never reach Home Assistant sensor states."""
    assert value_as_float("nan") is None
    assert value_as_float("inf") is None
    assert value_as_int(float("inf")) is None
