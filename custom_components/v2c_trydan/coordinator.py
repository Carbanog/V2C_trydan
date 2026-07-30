"""Data coordinator for V2C Trydan."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import V2CTrydanApi, V2CTrydanError, device_identifier
from .const import POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class V2CTrydanDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate one efficient poll shared by every charger entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: V2CTrydanApi,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.host = api.host
        self.device_id = (
            entry.unique_id
            if entry.unique_id and entry.unique_id != api.host
            else entry.entry_id
        )
        self._device_id_initialized = False
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"V2C Trydan {api.host}",
            update_interval=POLL_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the complete realtime payload."""
        try:
            data = await self.api.async_get_realtime_data()
        except V2CTrydanError as err:
            raise UpdateFailed(
                f"Error communicating with V2C Trydan at {self.host}: {err}"
            ) from err

        if not self._device_id_initialized:
            self.device_id = device_identifier(data, self.device_id)
            self._device_id_initialized = True
        return data
