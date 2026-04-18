"""Binary sensor platform for V2C Trydan."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class V2CBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a V2C Trydan binary sensor entity."""
    value_fn: Callable[[dict], bool]


TRYDAN_BINARY_SENSORS: tuple[V2CBinarySensorEntityDescription, ...] = (
    V2CBinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda data: int(data.get("ChargeState", 0)) in (1, 2),
    ),
    V2CBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda data: int(data.get("ChargeState", 0)) == 2,
    ),
    V2CBinarySensorEntityDescription(
        key="ready",
        translation_key="ready",
        value_fn=lambda data: int(data.get("ReadyState", 0)) == 1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan binary sensor platform."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        V2CtrydanBinarySensor(coordinator, description, config_entry.entry_id)
        for description in TRYDAN_BINARY_SENSORS
    )


class V2CtrydanBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a V2C Trydan binary sensor."""

    entity_description: V2CBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: V2CtrydanDataUpdateCoordinator,
        description: V2CBinarySensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.ip_address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.ip_address)},
            name=f"V2C Trydan ({coordinator.ip_address})",
            manufacturer="V2C",
            model="Trydan",
            configuration_url=f"http://{coordinator.ip_address}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if binary sensor is on."""
        if self.coordinator.data is None:
            return False
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception as err:
            _LOGGER.debug(f"Error obteniendo valor de {self.entity_description.key}: {err}")
            return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None