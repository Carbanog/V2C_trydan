"""Diagnostics support for V2C Trydan."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_IP_ADDRESS, SESSION_ACTIVE_TIME_KEY, SESSION_ENERGY_KEY
from .coordinator import V2CTrydanDataUpdateCoordinator
from .utils import value_as_float

_REDACT_CONFIG = {CONF_IP_ADDRESS}
_REDACT_DATA = {"ID", "IP", "SSID"}
_NUMERIC_DATA = frozenset(
    {
        "ChargeState",
        "ChargeMode",
        "ReadyState",
        "ChargePower",
        "VoltageInstallation",
        "ChargeEnergy",
        "SlaveError",
        "ChargeTime",
        "GridPower",
        "HousePower",
        "FVPower",
        "BatteryPower",
        "Paused",
        "Locked",
        "Timer",
        "Intensity",
        "IntensityMeasure_L1",
        "IntensityMeasure_L2",
        "IntensityMeasure_L3",
        "VoltageMeasure_L1",
        "VoltageMeasure_L2",
        "VoltageMeasure_L3",
        "Dynamic",
        "MinIntensity",
        "MaxIntensity",
        "PauseDynamic",
        "LightLED",
        "LogoLED",
        "DynamicPowerMode",
        "ContractedPower",
        "SignalStatus",
        SESSION_ENERGY_KEY,
        SESSION_ACTIVE_TIME_KEY,
    }
)


def _safe_telemetry(data: dict[str, Any]) -> dict[str, Any]:
    """Export only reviewed telemetry, never unknown firmware additions."""
    result = {
        key: value_as_float(value)
        for key, value in data.items()
        if key in _NUMERIC_DATA
    }
    result.update({key: "**REDACTED**" for key in _REDACT_DATA if key in data})
    firmware = data.get("FirmwareVersion")
    # Firmware identifiers are useful; arbitrary strings/nested data are not.
    if (
        isinstance(firmware, str)
        and len(firmware) <= 32
        and all(char.isdigit() or char in ".-bavrc" for char in firmware)
    ):
        result["FirmwareVersion"] = firmware
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for a config entry."""
    coordinator: V2CTrydanDataUpdateCoordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(
            {CONF_IP_ADDRESS: entry.data.get(CONF_IP_ADDRESS)}, _REDACT_CONFIG
        ),
        "data": _safe_telemetry(coordinator.data),
        "communication": coordinator.api.diagnostics,
    }
