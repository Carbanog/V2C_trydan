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
            if key == "Paused" and self.coordinator.scheduler is not None:
                await self.coordinator.scheduler.async_set_mode(
                    "paused" if value else "charge_now"
                )
                return
            await self.coordinator.api.async_write(key, value)
        except V2CTrydanError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class SchedulingEntity(V2CTrydanEntity):
    """Subscribe to policy changes as well as charger snapshots."""

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        if coordinator.scheduler is None:
            raise ValueError("Scheduling is not enabled")
        self.scheduler = coordinator.scheduler

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.scheduler.async_add_listener(self.async_write_ha_state)
        )
