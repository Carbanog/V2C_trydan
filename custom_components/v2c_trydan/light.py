"""Light platform for optional V2C Trydan LEDs."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .coordinator import V2CTrydanDataUpdateCoordinator
from .entity import V2CTrydanEntity
from .utils import value_as_int

_LED_SCALE = (0, 100)


@dataclass(frozen=True, kw_only=True)
class V2CLightEntityDescription(LightEntityDescription):
    """Describe a charger LED."""

    api_key: str
    supports_brightness: bool = False


LIGHTS: tuple[V2CLightEntityDescription, ...] = (
    V2CLightEntityDescription(
        key="light_led",
        translation_key="light_led",
        api_key="LightLED",
    ),
    V2CLightEntityDescription(
        key="logo_led",
        translation_key="logo_led",
        api_key="LogoLED",
        supports_brightness=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up LED entities supported by this charger's firmware."""
    coordinator: V2CTrydanDataUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        V2CTrydanLight(coordinator, description)
        for description in LIGHTS
        if value_as_int(coordinator.data.get(description.api_key)) is not None
    )


class V2CTrydanLight(V2CTrydanEntity, LightEntity):
    """Control one charger LED."""

    entity_description: V2CLightEntityDescription

    def __init__(
        self,
        coordinator: V2CTrydanDataUpdateCoordinator,
        description: V2CLightEntityDescription,
    ) -> None:
        """Initialize an LED entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_color_mode = (
            ColorMode.BRIGHTNESS if description.supports_brightness else ColorMode.ONOFF
        )
        self._attr_supported_color_modes = {self._attr_color_mode}

    @property
    def is_on(self) -> bool | None:
        """Return whether the LED is illuminated."""
        value = value_as_int(self.coordinator.data.get(self.entity_description.api_key))
        return value > 0 if value is not None else None

    @property
    def brightness(self) -> int | None:
        """Return Home Assistant brightness for the dimmable logo."""
        if not self.entity_description.supports_brightness:
            return None
        value = value_as_int(self.coordinator.data.get(self.entity_description.api_key))
        if value is None:
            return None
        return value_to_brightness(_LED_SCALE, value)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the LED, optionally setting logo brightness."""
        value = 100
        if self.entity_description.supports_brightness:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            value = round(brightness_to_value(_LED_SCALE, brightness))
            if brightness:
                value = max(value, 1)
        await self._async_write(self.entity_description.api_key, value)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the LED."""
        await self._async_write(self.entity_description.api_key, 0)
