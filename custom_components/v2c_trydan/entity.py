"""Shared entity support for V2C Trydan."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import V2CTrydanError
from .const import DOMAIN
from .coordinator import V2CTrydanDataUpdateCoordinator


class V2CTrydanEntity(CoordinatorEntity):
    """Base class for entities belonging to one V2C Trydan charger."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize common entity attributes."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer="V2C",
            model="Trydan",
            name=f"V2C Trydan ({coordinator.host})",
            configuration_url=coordinator.api.base_url,
            sw_version=coordinator.data.get("FirmwareVersion"),
        )

    async def _async_write(self, key: str, value: int) -> None:
        """Write a value and refresh all entities."""
        try:
            await self.coordinator.api.async_write(key, value)
        except V2CTrydanError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
