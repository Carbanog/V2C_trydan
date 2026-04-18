"""Switch platform for V2C Trydan."""
from __future__ import annotations

import logging
import aiohttp

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

TRYDAN_SWITCHES = ["Paused", "Dynamic", "Locked"]

SWITCH_TRANSLATION_KEY_MAP = {
    "Dynamic": "dynamic",
    "Paused": "paused",
    "Locked": "locked",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan switch platform."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        V2CtrydanSwitch(coordinator, key)
        for key in TRYDAN_SWITCHES
    )


class V2CtrydanSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a V2C Trydan switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: V2CtrydanDataUpdateCoordinator,
        data_key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_translation_key = SWITCH_TRANSLATION_KEY_MAP.get(data_key)
        self._attr_unique_id = f"{coordinator.ip_address}_{data_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.ip_address)},
            name=f"V2C Trydan ({coordinator.ip_address})",
            manufacturer="V2C",
            model="Trydan",
            configuration_url=f"http://{coordinator.ip_address}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if self.coordinator.data is None:
            return False
        return bool(self.coordinator.data.get(self._data_key, False))

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.coordinator.ip_address}/write/{self._data_key}=1"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                await self.coordinator.async_request_refresh()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error activando switch {self._data_key}: {err}")
            raise

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.coordinator.ip_address}/write/{self._data_key}=0"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                await self.coordinator.async_request_refresh()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error desactivando switch {self._data_key}: {err}")
            raise