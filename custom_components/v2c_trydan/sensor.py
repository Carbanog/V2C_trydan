"""Support for V2C Trydan sensors."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_float, value_as_int


@dataclass(frozen=True, kw_only=True)
class V2CSensorEntityDescription(SensorEntityDescription):
    """Describes a V2C Trydan sensor entity."""

    value_fn: Callable[[Mapping[str, Any]], Any]


def _rounded_float(value: Any) -> int | None:
    """Convert a numeric charger value to rounded watts."""
    converted = value_as_float(value)
    return round(converted) if converted is not None else None


def _integer_string(value: Any) -> str | None:
    """Return the integer value formatted for an enum sensor."""
    converted = value_as_int(value)
    return str(converted) if converted is not None else None


TRYDAN_SENSORS: tuple[V2CSensorEntityDescription, ...] = (
    V2CSensorEntityDescription(
        key="charge_power",
        translation_key="chargepower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: _rounded_float(data.get("ChargePower")),
    ),
    V2CSensorEntityDescription(
        key="charge_energy",
        translation_key="chargeenergy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        value_fn=lambda data: value_as_float(data.get("ChargeEnergy")),
    ),
    V2CSensorEntityDescription(
        key="charge_state",
        translation_key="chargestate",
        device_class=SensorDeviceClass.ENUM,
        options=["0", "1", "2", "3", "4", "5"],
        value_fn=lambda data: _integer_string(data.get("ChargeState")),
    ),
    V2CSensorEntityDescription(
        key="charge_time",
        translation_key="chargetime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: value_as_float(data.get("ChargeTime")),
    ),
    V2CSensorEntityDescription(
        key="house_power",
        translation_key="housepower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: _rounded_float(data.get("HousePower")),
    ),
    V2CSensorEntityDescription(
        key="fv_power",
        translation_key="fvpower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: _rounded_float(data.get("FVPower")),
    ),
    V2CSensorEntityDescription(
        key="battery_power",
        translation_key="batterypower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: _rounded_float(data.get("BatteryPower")),
    ),
    V2CSensorEntityDescription(
        key="intensity",
        translation_key="intensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: value_as_float(data.get("Intensity")),
    ),
    V2CSensorEntityDescription(
        key="min_intensity",
        translation_key="minintensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: value_as_float(data.get("MinIntensity")),
    ),
    V2CSensorEntityDescription(
        key="max_intensity",
        translation_key="maxintensity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: value_as_float(data.get("MaxIntensity")),
    ),
    V2CSensorEntityDescription(
        key="voltage_installation",
        translation_key="voltageinstallation",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        value_fn=lambda data: value_as_float(data.get("VoltageInstallation")),
    ),
    V2CSensorEntityDescription(
        key="contracted_power",
        translation_key="contractedpower",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: value_as_float(data.get("ContractedPower")),
    ),
    V2CSensorEntityDescription(
        key="dynamic",
        translation_key="dynamic",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("Dynamic"),
    ),
    V2CSensorEntityDescription(
        key="dynamic_power_mode",
        translation_key="dynamicpowermode",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("DynamicPowerMode"),
    ),
    V2CSensorEntityDescription(
        key="locked",
        translation_key="locked",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("Locked"),
    ),
    V2CSensorEntityDescription(
        key="paused",
        translation_key="paused",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
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
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up V2C Trydan sensor platform."""
    coordinator = config_entry.runtime_data

    async_add_entities(
        V2CTrydanSensor(coordinator, description) for description in TRYDAN_SENSORS
    )


class V2CTrydanSensor(V2CTrydanEntity, SensorEntity):
    """Representation of a V2C Trydan sensor."""

    entity_description: V2CSensorEntityDescription

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        description: V2CSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
