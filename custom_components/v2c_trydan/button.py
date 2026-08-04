"""Button platform for V2C Trydan maintenance actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up optional session maintenance controls."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities((ResetSessionStatisticsButton(coordinator),))


class ResetSessionStatisticsButton(V2CTrydanEntity, ButtonEntity):
    """Allow an exceptional manual reset of the local session statistics."""

    _attr_translation_key = "reset_session_energy"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:restore"

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "reset_session_energy")

    async def async_press(self) -> None:
        """Reset session totals while preserving current raw baselines."""
        await self.coordinator.async_reset_session_statistics()
