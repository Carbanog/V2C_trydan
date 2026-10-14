"""Tests for defensive charger value conversion."""

from __future__ import annotations

from custom_components.v2c_trydan.utils import (
    cable_connected_from_charge_state,
    value_as_bool,
    value_as_float,
    value_as_int,
)


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
