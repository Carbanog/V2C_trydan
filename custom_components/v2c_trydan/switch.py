"""Switch platform for V2C Trydan."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_bool


@dataclass(frozen=True, kw_only=True)
class V2CSwitchEntityDescription(SwitchEntityDescription):
    """Describe a charger switch."""

    api_key: str


SWITCHES: tuple[V2CSwitchEntityDescription, ...] = (
    V2CSwitchEntityDescription(
        key="Paused",
        translation_key="paused",
        api_key="Paused",
    ),
    V2CSwitchEntityDescription(
        key="Dynamic",
        translation_key="dynamic",
        api_key="Dynamic",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    V2CSwitchEntityDescription(
        key="Locked",
        translation_key="locked",
        api_key="Locked",
    ),
    V2CSwitchEntityDescription(
        key="timer",
        translation_key="timer",
        api_key="Timer",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    V2CSwitchEntityDescription(
        key="pause_dynamic",
        translation_key="pause_dynamic",
        api_key="PauseDynamic",
        icon="mdi:pause",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan switches."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        V2CTrydanSwitch(coordinator, description)
        for description in SWITCHES
        if description.api_key in coordinator.data
    )


class V2CTrydanSwitch(V2CTrydanEntity, SwitchEntity):
    """Representation of a charger switch."""

    entity_description: V2CSwitchEntityDescription

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        description: V2CSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the switch state without treating the string '0' as on."""
        return value_as_bool(self.coordinator.data.get(self.entity_description.api_key))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_write(self.entity_description.api_key, 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_write(self.entity_description.api_key, 0)
