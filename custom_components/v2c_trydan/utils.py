"""Pure value conversion helpers for V2C Trydan."""

from __future__ import annotations

from math import isfinite
from typing import Any

from .const import MAX_INTENSITY, MIN_INTENSITY


def value_as_int(value: Any) -> int | None:
    """Return an integer representation of a charger value."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (OverflowError, TypeError, ValueError):
        return None


def value_as_float(value: Any) -> float | None:
    """Return a float representation of a charger value."""
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return converted if isfinite(converted) else None


def value_as_bool(value: Any) -> bool | None:
    """Return a boolean representation of common charger values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on"}:
            return True
        if normalized in {"0", "false", "off"}:
            return False
    return None


def cable_connected_from_charge_state(value: Any) -> bool | None:
    """Only an explicit unplugged state proves the end of a cable session.

    Faults and ventilation requests do not tell us whether the cable was
    removed. Preserve the session until the next explicit cable state.
    """
    state = value_as_float(value)
    if state == 0:
        return False
    if state in (1, 2):
        return True
    return None


def validate_intensity(key: str, value: object, data: dict[str, Any]) -> None:
    """Validate every current control against the latest observed charger limits.

    Service calls bypass number entity bounds. Unknown counterpart limits must
    not silently turn into permission to send a potentially conflicting value.
    """
    current = value_as_float(value)
    if (
        current is None
        or not current.is_integer()
        or not MIN_INTENSITY <= current <= MAX_INTENSITY
    ):
        raise ValueError(
            f"Intensity must be a whole number from "
            f"{MIN_INTENSITY} to {MAX_INTENSITY} A"
        )
    lower = value_as_float(data.get("MinIntensity"))
    upper = value_as_float(data.get("MaxIntensity"))
    if key in {"MaxIntensity", "Intensity"}:
        if lower is None or not MIN_INTENSITY <= lower <= MAX_INTENSITY:
            raise ValueError("The charger minimum intensity is unavailable or invalid")
        if current < lower:
            raise ValueError("Intensity cannot be below the charger minimum")
    if key in {"MinIntensity", "Intensity"}:
        if upper is None or not MIN_INTENSITY <= upper <= MAX_INTENSITY:
            raise ValueError("The charger maximum intensity is unavailable or invalid")
        if current > upper:
            raise ValueError("Intensity cannot exceed the charger maximum")
