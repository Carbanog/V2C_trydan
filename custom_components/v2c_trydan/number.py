"""Number platform for V2C Trydan."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MAX_INTENSITY, MIN_INTENSITY
from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_float


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan number entities."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        (
            MaxIntensityNumber(coordinator),
            MinIntensityNumber(coordinator),
            IntensityNumber(coordinator),
        )
    )


class V2CNumberEntity(V2CTrydanEntity, NumberEntity):
    """Base class for charger current controls."""

    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_icon = "mdi:current-ac"

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        entity_key: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entity_key)


class MaxIntensityNumber(V2CNumberEntity):
    """Maximum dynamic charging intensity."""

    _attr_translation_key = "max_intensity"
    _attr_native_max_value = MAX_INTENSITY

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator) -> None:
        """Initialize the maximum intensity control."""
        super().__init__(coordinator, "max_intensity")

    @property
    def native_value(self) -> float | None:
        """Return the configured maximum intensity."""
        return value_as_float(self.coordinator.data.get("MaxIntensity"))

    @property
    def native_min_value(self) -> float:
        """Keep the maximum at or above the configured minimum."""
        return (
            value_as_float(self.coordinator.data.get("MinIntensity")) or MIN_INTENSITY
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the maximum intensity."""
        await self._async_write("MaxIntensity", int(value))


class MinIntensityNumber(V2CNumberEntity):
    """Minimum dynamic charging intensity."""

    _attr_translation_key = "min_intensity"
    _attr_native_min_value = MIN_INTENSITY

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator) -> None:
        """Initialize the minimum intensity control."""
        super().__init__(coordinator, "min_intensity")

    @property
    def native_value(self) -> float | None:
        """Return the configured minimum intensity."""
        return value_as_float(self.coordinator.data.get("MinIntensity"))

    @property
    def native_max_value(self) -> float:
        """Keep the minimum at or below the configured maximum."""
        return (
            value_as_float(self.coordinator.data.get("MaxIntensity")) or MAX_INTENSITY
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the minimum intensity."""
        await self._async_write("MinIntensity", int(value))


class IntensityNumber(V2CNumberEntity):
    """Manual charging intensity."""

    _attr_translation_key = "intensity"

    def __init__(self, coordinator: V2CTrydanDataUpdateCoordinator) -> None:
        """Initialize the manual intensity control."""
        super().__init__(coordinator, "intensity")

    @property
    def native_value(self) -> float | None:
        """Return the current manual intensity."""
        return value_as_float(self.coordinator.data.get("Intensity"))

    @property
    def native_min_value(self) -> float:
        """Return the active lower limit."""
        return (
            value_as_float(self.coordinator.data.get("MinIntensity")) or MIN_INTENSITY
        )

    @property
    def native_max_value(self) -> float:
        """Return the active upper limit."""
        return (
            value_as_float(self.coordinator.data.get("MaxIntensity")) or MAX_INTENSITY
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the manual intensity."""
        await self._async_write("Intensity", int(value))
