"""Select platform for V2C Trydan."""
from __future__ import annotations

import logging
import aiohttp

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DYNAMIC_POWER_MODE_OPTIONS = [
    "enable_timed_power",
    "disable_timed_power",
    "disable_timed_power_exclusive",
    "disable_timed_power_min",
    "disable_timed_power_grid_fv",
    "disable_timed_power_stop",
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan select platform."""
    coordinator = config_entry.runtime_data
    async_add_entities([DynamicPowerModeSelect(coordinator)])


class DynamicPowerModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of Dynamic Power Mode selector."""

    _attr_has_entity_name = True
    _attr_translation_key = "dynamic_power_mode"
    _attr_options = DYNAMIC_POWER_MODE_OPTIONS

    def __init__(self, coordinator: V2CtrydanDataUpdateCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.ip_address}_dynamic_power_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.ip_address)},
            name=f"V2C Trydan ({coordinator.ip_address})",
            manufacturer="V2C",
            model="Trydan",
            configuration_url=f"http://{coordinator.ip_address}",
        )

    @property
    def current_option(self) -> str | None:
        """Return current option from coordinator data."""
        if self.coordinator.data is None:
            return None
        mode = self.coordinator.data.get("DynamicPowerMode")
        if mode is not None and 0 <= int(mode) <= 5:
            return DYNAMIC_POWER_MODE_OPTIONS[int(mode)]
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in DYNAMIC_POWER_MODE_OPTIONS:
            _LOGGER.error(f"Opción inválida: {option}")
            return

        mode_value = DYNAMIC_POWER_MODE_OPTIONS.index(option)
        session = async_get_clientsession(self.hass)
        url = f"http://{self.coordinator.ip_address}/write/DynamicPowerMode={mode_value}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                response_text = await response.text()
                if response_text.strip().upper() == "ERROR":
                    raise ValueError(f"El dispositivo rechazó el modo {mode_value}")
                await self.coordinator.async_request_refresh()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error estableciendo modo dinámico {mode_value}: {err}")
            raise