"""Binary sensor platform for V2C Trydan."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_int


@dataclass(frozen=True, kw_only=True)
class V2CBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a V2C Trydan binary sensor."""

    value_fn: Callable[[Mapping[str, Any]], bool | None]


def _charge_state_is(
    data: Mapping[str, Any], accepted_states: tuple[int, ...]
) -> bool | None:
    """Evaluate a charge state while preserving an unknown value."""
    state = value_as_int(data.get("ChargeState"))
    return state in accepted_states if state is not None else None


BINARY_SENSORS: tuple[V2CBinarySensorEntityDescription, ...] = (
    V2CBinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda data: _charge_state_is(data, (1, 2)),
    ),
    V2CBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda data: _charge_state_is(data, (2,)),
    ),
    V2CBinarySensorEntityDescription(
        key="ready",
        translation_key="ready",
        value_fn=lambda data: (
            value_as_int(data.get("ReadyState")) == 1
            if value_as_int(data.get("ReadyState")) is not None
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan binary sensors."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        V2CTrydanBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class V2CTrydanBinarySensor(V2CTrydanEntity, BinarySensorEntity):
    """Representation of a V2C Trydan binary sensor."""

    entity_description: V2CBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        description: V2CBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return whether the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data)
