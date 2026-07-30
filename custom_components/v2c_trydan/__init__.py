"""The V2C Trydan integration."""

from __future__ import annotations

from collections.abc import Mapping

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import V2CTrydanApi, V2CTrydanError
from .const import (
    CONF_CONFIG_ENTRY_ID,
    CONF_IP_ADDRESS,
    DOMAIN,
    MAX_DYNAMIC_POWER_MODE,
    MAX_INTENSITY,
    MIN_DYNAMIC_POWER_MODE,
    MIN_INTENSITY,
    SERVICE_SET_DYNAMIC_POWER_MODE,
    SERVICE_SET_INTENSITY,
    SERVICE_SET_MAX_INTENSITY,
    SERVICE_SET_MIN_INTENSITY,
)
from .coordinator import V2CTrydanDataUpdateCoordinator

PLATFORMS: tuple[Platform, ...] = (
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.LIGHT,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_DYNAMIC_POWER_MODE_VALIDATOR = vol.All(
    vol.Coerce(int),
    vol.Range(
        min=MIN_DYNAMIC_POWER_MODE,
        max=MAX_DYNAMIC_POWER_MODE,
    ),
)

_SERVICE_DEFINITIONS: Mapping[str, tuple[str, str, vol.Schema]] = {
    SERVICE_SET_INTENSITY: (
        "intensity",
        "Intensity",
        vol.Schema(
            {
                vol.Required("intensity"): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_INTENSITY, max=MAX_INTENSITY)
                ),
                vol.Optional(CONF_CONFIG_ENTRY_ID): str,
            }
        ),
    ),
    SERVICE_SET_MIN_INTENSITY: (
        "min_intensity",
        "MinIntensity",
        vol.Schema(
            {
                vol.Required("min_intensity"): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_INTENSITY, max=MAX_INTENSITY)
                ),
                vol.Optional(CONF_CONFIG_ENTRY_ID): str,
            }
        ),
    ),
    SERVICE_SET_MAX_INTENSITY: (
        "max_intensity",
        "MaxIntensity",
        vol.Schema(
            {
                vol.Required("max_intensity"): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_INTENSITY, max=MAX_INTENSITY)
                ),
                vol.Optional(CONF_CONFIG_ENTRY_ID): str,
            }
        ),
    ),
    SERVICE_SET_DYNAMIC_POWER_MODE: (
        "dynamic_power_mode",
        "DynamicPowerMode",
        vol.Any(
            vol.Schema(
                {
                    vol.Required("dynamic_power_mode"): _DYNAMIC_POWER_MODE_VALIDATOR,
                    vol.Optional(CONF_CONFIG_ENTRY_ID): str,
                }
            ),
            # Releases through 1.2.2 exposed this charger API key directly.
            # Accept it as an alias so existing scripts and automations keep working.
            vol.Schema(
                {
                    vol.Required("DynamicPowerMode"): _DYNAMIC_POWER_MODE_VALIDATOR,
                    vol.Optional(CONF_CONFIG_ENTRY_ID): str,
                }
            ),
        ),
    ),
}

# These are the suffixes used by releases up to 1.2.2. Keeping the map here
# makes the one-time registry migration explicit and protects user customizations.
_LEGACY_ENTITY_SUFFIXES: Mapping[Platform, tuple[str, ...]] = {
    Platform.BINARY_SENSOR: ("connected", "charging", "ready"),
    Platform.NUMBER: ("max_intensity", "min_intensity", "intensity"),
    Platform.SELECT: ("dynamic_power_mode",),
    Platform.SWITCH: ("Paused", "Dynamic", "Locked"),
    Platform.SENSOR: (
        "charge_power",
        "charge_energy",
        "charge_state",
        "charge_time",
        "house_power",
        "fv_power",
        "battery_power",
        "intensity",
        "min_intensity",
        "max_intensity",
        "voltage_installation",
        "contracted_power",
        "dynamic",
        "dynamic_power_mode",
        "locked",
        "paused",
        "pause_dynamic",
        "slave_error",
        "timer",
        "firmware_version",
        "ip_address",
        "ssid",
        "signal_status",
        "device_id",
        "ready_state",
    ),
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-level actions."""

    async def async_handle_service(call: ServiceCall) -> None:
        service_definition = _SERVICE_DEFINITIONS[call.service]
        field, charger_key, _schema = service_definition
        coordinator = _resolve_service_coordinator(hass, call)
        value = call.data.get(field)
        if field == "dynamic_power_mode" and value is None:
            value = call.data["DynamicPowerMode"]

        try:
            await coordinator.api.async_write(charger_key, value)
        except V2CTrydanError as err:
            raise ServiceValidationError(str(err)) from err
        await coordinator.async_request_refresh()

    for service_name, (_field, _charger_key, schema) in _SERVICE_DEFINITIONS.items():
        hass.services.async_register(
            DOMAIN,
            service_name,
            async_handle_service,
            schema=schema,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up V2C Trydan from a config entry."""
    host = entry.data[CONF_IP_ADDRESS]
    api = V2CTrydanApi(async_get_clientsession(hass), host)
    coordinator = V2CTrydanDataUpdateCoordinator(hass, entry, api)

    # The coordinator converts an unavailable charger into ConfigEntryNotReady,
    # allowing Home Assistant to retry setup without requiring a restart.
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _migrate_legacy_registry_entries(hass, entry, coordinator.device_id)
    _migrate_config_entry_unique_id(hass, entry, coordinator.device_id)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.device_id)},
        manufacturer="V2C",
        model="Trydan",
        name=f"V2C Trydan ({host})",
        configuration_url=api.base_url,
        sw_version=coordinator.data.get("FirmwareVersion"),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older config entry metadata."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, version=2)
    return True


def _resolve_service_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> V2CTrydanDataUpdateCoordinator:
    """Resolve the charger targeted by a backwards-compatible action."""
    requested_entry_id = call.data.get(CONF_CONFIG_ENTRY_ID)
    loaded_entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]

    if requested_entry_id:
        loaded_entries = [
            entry for entry in loaded_entries if entry.entry_id == requested_entry_id
        ]

    if len(loaded_entries) != 1:
        if requested_entry_id:
            message = "The selected V2C Trydan config entry is not loaded"
        elif not loaded_entries:
            message = "No V2C Trydan charger is currently loaded"
        else:
            message = (
                "Select a V2C Trydan config entry when more than one charger "
                "is configured"
            )
        raise ServiceValidationError(message)

    return loaded_entries[0].runtime_data


def _migrate_config_entry_unique_id(
    hass: HomeAssistant, entry: ConfigEntry, device_id: str
) -> None:
    """Replace the legacy IP unique ID when the hardware ID is available."""
    if entry.unique_id == device_id:
        return
    has_collision = any(
        other.entry_id != entry.entry_id and other.unique_id == device_id
        for other in hass.config_entries.async_entries(DOMAIN)
    )
    if not has_collision:
        hass.config_entries.async_update_entry(entry, unique_id=device_id)


def _migrate_legacy_registry_entries(
    hass: HomeAssistant, entry: ConfigEntry, device_id: str
) -> None:
    """Move IP-based device/entity identifiers to the hardware identifier."""
    legacy_id = entry.data[CONF_IP_ADDRESS]
    if legacy_id == device_id:
        return

    device_registry = dr.async_get(hass)
    legacy_device = device_registry.async_get_device(identifiers={(DOMAIN, legacy_id)})
    current_device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
    if legacy_device is not None and current_device is None:
        device_registry.async_update_device(
            legacy_device.id,
            new_identifiers={(DOMAIN, device_id)},
        )

    entity_registry = er.async_get(hass)
    for platform, suffixes in _LEGACY_ENTITY_SUFFIXES.items():
        for suffix in suffixes:
            new_unique_id = f"{device_id}_{suffix}"
            entity_id = entity_registry.async_get_entity_id(
                platform, DOMAIN, f"{legacy_id}_{suffix}"
            )
            existing_entity_id = entity_registry.async_get_entity_id(
                platform, DOMAIN, new_unique_id
            )
            if entity_id is not None and existing_entity_id is None:
                entity_registry.async_update_entity(
                    entity_id,
                    new_unique_id=new_unique_id,
                )
