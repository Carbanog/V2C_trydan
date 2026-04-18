"""Support for V2C Trydan sensors."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricCurrent,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class V2CSensorEntityDescription(SensorEntityDescription):
    """Describes a V2C Trydan sensor entity."""
    value_fn: Callable[[dict], any]


TRYDAN_SENSORS: tuple[V2CSensorEntityDescription, ...] = (
    V2CSensorEntityDescription(
        key="charge_power",
        translation_key="chargepower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: round(float(data["ChargePower"])) if data.get("ChargePower") is not None else None,
    ),
    V2CSensorEntityDescription(
        key="charge_energy",
        translation_key="chargeenergy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda data: data.get("ChargeEnergy"),
    ),
    V2CSensorEntityDescription(
        key="charge_state",
        translation_key="chargestate",
        device_class=SensorDeviceClass.ENUM,
        options=["0", "1", "2"],
        value_fn=lambda data: str(data.get("ChargeState")) if data.get("ChargeState") is not None else None,
    ),
    V2CSensorEntityDescription(
        key="charge_time",
        translation_key="chargetime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.get("ChargeTime"),
    ),
    V2CSensorEntityDescription(
        key="house_power",
        translation_key="housepower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: round(float(data["HousePower"])) if data.get("HousePower") is not None else None,
    ),
    V2CSensorEntityDescription(
        key="fv_power",
        translation_key="fvpower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: round(float(data["FVPower"])) if data.get("FVPower") is not None else None,
    ),
    V2CSensorEntityDescription(
        key="battery_power",
        translation_key="batterypower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: round(float(data["BatteryPower"])) if data.get("BatteryPower") is not None else None,
    ),
    V2CSensorEntityDescription(
        key="intensity",
        translation_key="intensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.get("Intensity"),
    ),
    V2CSensorEntityDescription(
        key="min_intensity",
        translation_key="minintensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.get("MinIntensity"),
    ),
    V2CSensorEntityDescription(
        key="max_intensity",
        translation_key="maxintensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.get("MaxIntensity"),
    ),
    V2CSensorEntityDescription(
        key="voltage_installation",
        translation_key="voltageinstallation",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        value_fn=lambda data: data.get("VoltageInstallation"),
    ),
    V2CSensorEntityDescription(
        key="contracted_power",
        translation_key="contractedpower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: data.get("ContractedPower"),
    ),
    V2CSensorEntityDescription(
        key="dynamic",
        translation_key="dynamic",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("Dynamic"),
    ),
    V2CSensorEntityDescription(
        key="dynamic_power_mode",
        translation_key="dynamicpowermode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("DynamicPowerMode"),
    ),
    V2CSensorEntityDescription(
        key="locked",
        translation_key="locked",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("Locked"),
    ),
    V2CSensorEntityDescription(
        key="paused",
        translation_key="paused",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("Paused"),
    ),
    V2CSensorEntityDescription(
        key="pause_dynamic",
        translation_key="pausedynamic",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("PauseDynamic"),
    ),
    V2CSensorEntityDescription(
        key="slave_error",
        translation_key="slaveerror",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("SlaveError"),
    ),
    V2CSensorEntityDescription(
        key="timer",
        translation_key="timer",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("Timer"),
    ),
    V2CSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("FirmwareVersion"),
    ),
    V2CSensorEntityDescription(
        key="ip_address",
        translation_key="ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("IP"),
    ),
    V2CSensorEntityDescription(
        key="ssid",
        translation_key="ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("SSID"),
    ),
    V2CSensorEntityDescription(
        key="signal_status",
        translation_key="signalstatus",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("SignalStatus"),
    ),
    V2CSensorEntityDescription(
        key="device_id",
        translation_key="id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ID"),
    ),
    V2CSensorEntityDescription(
        key="ready_state",
        translation_key="readystate",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ReadyState"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan sensor platform."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        V2CtrydanSensor(coordinator, description, config_entry.entry_id)
        for description in TRYDAN_SENSORS
    )


class V2CtrydanSensor(CoordinatorEntity, SensorEntity):
    """Representation of a V2C Trydan sensor."""

    entity_description: V2CSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: V2CtrydanDataUpdateCoordinator,
        description: V2CSensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception as err:
            _LOGGER.debug(f"Error obteniendo valor de {self.entity_description.key}: {err}")
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None