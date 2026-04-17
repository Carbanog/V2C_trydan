"""The v2c_trydan component."""
from __future__ import annotations

import logging
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_IP_ADDRESS
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up V2C Trydan from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    ip_address = entry.data[CONF_IP_ADDRESS]

    coordinator = V2CtrydanDataUpdateCoordinator(hass, ip_address)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, ip_address)},
        manufacturer="V2C",
        model="Trydan",
        name=f"V2C Trydan ({ip_address})",
        configuration_url=f"http://{ip_address}",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services
    async def set_intensity(call: ServiceCall) -> None:
        """Set charging intensity."""
        value = call.data.get("intensity")
        try:
            value = int(value)
            if 6 <= value <= 32:
                await _async_write(hass, ip_address, "Intensity", value)
            else:
                _LOGGER.error("intensity debe estar entre 6 y 32")
        except (ValueError, TypeError):
            _LOGGER.error(f"intensity inválida: {value}")

    async def set_min_intensity(call: ServiceCall) -> None:
        """Set minimum charging intensity."""
        value = call.data.get("min_intensity")
        try:
            value = int(value)
            if 6 <= value <= 32:
                await _async_write(hass, ip_address, "MinIntensity", value)
            else:
                _LOGGER.error("min_intensity debe estar entre 6 y 32")
        except (ValueError, TypeError):
            _LOGGER.error(f"min_intensity inválida: {value}")

    async def set_max_intensity(call: ServiceCall) -> None:
        """Set maximum charging intensity."""
        value = call.data.get("max_intensity")
        try:
            value = int(value)
            if 6 <= value <= 32:
                await _async_write(hass, ip_address, "MaxIntensity", value)
            else:
                _LOGGER.error("max_intensity debe estar entre 6 y 32")
        except (ValueError, TypeError):
            _LOGGER.error(f"max_intensity inválida: {value}")

    async def set_dynamic_power_mode(call: ServiceCall) -> None:
        """Set dynamic power mode."""
        value = call.data.get("DynamicPowerMode")
        try:
            value = int(value)
            if 0 <= value <= 5:
                await _async_write(hass, ip_address, "DynamicPowerMode", value)
            else:
                _LOGGER.error("DynamicPowerMode debe estar entre 0 y 5")
        except (ValueError, TypeError):
            _LOGGER.error(f"DynamicPowerMode inválido: {value}")

    hass.services.async_register(DOMAIN, "set_intensity", set_intensity)
    hass.services.async_register(DOMAIN, "set_min_intensity", set_min_intensity)
    hass.services.async_register(DOMAIN, "set_max_intensity", set_max_intensity)
    hass.services.async_register(DOMAIN, "set_dynamic_power_mode", set_dynamic_power_mode)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_write(hass: HomeAssistant, ip_address: str, key: str, value: int) -> None:
    """Send write command to device."""
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/{key}={value}"
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            response.raise_for_status()
            _LOGGER.debug(f"{key} establecido a {value} en {ip_address}")
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error escribiendo {key}={value}: {err}")