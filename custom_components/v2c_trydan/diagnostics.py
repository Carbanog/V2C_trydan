"""Diagnostics support for V2C Trydan."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_IP_ADDRESS
from .coordinator import V2CTrydanDataUpdateCoordinator

_REDACT_CONFIG = {CONF_IP_ADDRESS}
_REDACT_DATA = {"ID", "IP", "SSID"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-safe diagnostics for a config entry."""
    coordinator: V2CTrydanDataUpdateCoordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(dict(entry.data), _REDACT_CONFIG),
        "data": async_redact_data(dict(coordinator.data), _REDACT_DATA),
    }
