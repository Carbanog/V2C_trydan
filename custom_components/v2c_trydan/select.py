"""Select platform for V2C Trydan."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_int

DYNAMIC_POWER_MODE_OPTIONS: tuple[str, ...] = (
    "enable_timed_power",
    "disable_timed_power",
    "disable_timed_power_exclusive",
    "disable_timed_power_min",
    "disable_timed_power_grid_fv",
    "disable_timed_power_stop",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the dynamic power mode selector."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities((DynamicPowerModeSelect(coordinator),))


class DynamicPowerModeSelect(V2CTrydanEntity, SelectEntity):
    """Control the charger's dynamic power strategy."""

    _attr_translation_key = "dynamic_power_mode"
    _attr_options = DYNAMIC_POWER_MODE_OPTIONS

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator) -> None:
        """Initialize the selector."""
        super().__init__(coordinator, "dynamic_power_mode")

    @property
    def current_option(self) -> str | None:
        """Return the current strategy."""
        mode = value_as_int(self.coordinator.data.get("DynamicPowerMode"))
        if mode is None or not 0 <= mode < len(DYNAMIC_POWER_MODE_OPTIONS):
            return None
        return DYNAMIC_POWER_MODE_OPTIONS[mode]

    async def async_select_option(self, option: str) -> None:
        """Change the dynamic power strategy."""
        try:
            mode = DYNAMIC_POWER_MODE_OPTIONS.index(option)
        except ValueError as err:
            raise HomeAssistantError(
                f"Unsupported dynamic power mode: {option}"
            ) from err
        await self._async_write("DynamicPowerMode", mode)
