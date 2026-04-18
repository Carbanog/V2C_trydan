"""Number platform for V2C Trydan."""
from __future__ import annotations

import logging
import aiohttp

from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan number platform."""
    coordinator = config_entry.runtime_data

    async_add_entities([
        MaxIntensityNumber(coordinator),
        MinIntensityNumber(coordinator),
        IntensityNumber(coordinator),
    ])


class V2CNumberBase(CoordinatorEntity, NumberEntity):
    """Base class for V2C Trydan number entities."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "A"
    _attr_icon = "mdi:current-ac"

    def __init__(self, coordinator: V2CtrydanDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.ip_address)},
            name=f"V2C Trydan ({coordinator.ip_address})",
            manufacturer="V2C",
            model="Trydan",
            configuration_url=f"http://{coordinator.ip_address}",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    async def _send_value(self, key: str, value: int) -> None:
        """Send value to device."""
        session = async_get_clientsession(self.hass)
        url = f"http://{self.coordinator.ip_address}/write/{key}={value}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                response_text = await response.text()
                if response_text.strip().upper() == "ERROR":
                    raise ValueError(f"El dispositivo rechazó el valor {value} para {key}")
                await self.coordinator.async_request_refresh()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error enviando {key}={value}: {err}")
            raise


class MaxIntensityNumber(V2CNumberBase):
    """Maximum charging intensity."""

    _attr_translation_key = "max_intensity"

    def __init__(self, coordinator: V2CtrydanDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.ip_address}_max_intensity"

    @property
    def native_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MaxIntensity", 32)
        return 32

    @property
    def native_max_value(self) -> float:
        return 32

    @property
    def native_min_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MinIntensity", 6)
        return 6

    async def async_set_native_value(self, value: float) -> None:
        await self._send_value("MaxIntensity", int(value))


class MinIntensityNumber(V2CNumberBase):
    """Minimum charging intensity."""

    _attr_translation_key = "min_intensity"

    def __init__(self, coordinator: V2CtrydanDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.ip_address}_min_intensity"

    @property
    def native_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MinIntensity", 6)
        return 6

    @property
    def native_max_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MaxIntensity", 32)
        return 32

    @property
    def native_min_value(self) -> float:
        return 6

    async def async_set_native_value(self, value: float) -> None:
        await self._send_value("MinIntensity", int(value))


class IntensityNumber(V2CNumberBase):
    """Current charging intensity."""

    _attr_translation_key = "intensity"

    def __init__(self, coordinator: V2CtrydanDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.ip_address}_intensity"

    @property
    def native_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("Intensity", 6)
        return 6

    @property
    def native_max_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MaxIntensity", 32)
        return 32

    @property
    def native_min_value(self) -> float:
        if self.coordinator.data:
            return self.coordinator.data.get("MinIntensity", 6)
        return 6

    async def async_set_native_value(self, value: float) -> None:
        await self._send_value("Intensity", int(value))