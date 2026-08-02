"""Pure value conversion helpers for V2C Trydan."""

from __future__ import annotations

from math import isfinite
from typing import Any


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
