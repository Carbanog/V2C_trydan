"""Data coordinator for V2C Trydan."""

from __future__ import annotations

import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import V2CTrydanApi, V2CTrydanError, device_identifier
from .const import DOMAIN, POLL_INTERVAL, SESSION_ACTIVE_TIME_KEY, SESSION_ENERGY_KEY
from .session import SessionState, SessionTracker

_LOGGER = logging.getLogger(__name__)

SESSION_STORE_VERSION = 1
_SESSION_SAVE_INTERVAL = 60


def session_store_key(entry_id: str) -> str:
    """Return the stable storage key first introduced for session energy."""
    # Keep the legacy suffix so upgrading from b4 preserves its checkpoint.
    return f"{DOMAIN}.{entry_id}.session_energy"


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
        self._session_tracker = SessionTracker()
        self._session_store: Store[dict[str, Any]] = Store(
            hass,
            SESSION_STORE_VERSION,
            session_store_key(entry.entry_id),
            atomic_writes=True,
        )
        self._last_session_save = monotonic()
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"V2C Trydan {api.host}",
            update_interval=POLL_INTERVAL,
            always_update=False,
        )

    async def async_initialize(self) -> None:
        """Restore session accumulation before the first charger poll."""
        stored_state = await self._session_store.async_load()
        self._session_tracker = SessionTracker(SessionState.from_dict(stored_state))
        self._last_session_save = monotonic()

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

        session_update = self._session_tracker.update(
            data.get("ChargeState"),
            data.get("ChargeEnergy"),
            data.get("ChargeTime"),
        )
        data[SESSION_ENERGY_KEY] = self._session_tracker.energy
        data[SESSION_ACTIVE_TIME_KEY] = self._session_tracker.active_time
        if session_update.changed and (
            session_update.connection_changed
            or monotonic() - self._last_session_save >= _SESSION_SAVE_INTERVAL
        ):
            await self._async_save_session()
        return data

    async def async_reset_session_statistics(self) -> None:
        """Reset accumulated session statistics and publish immediately."""
        self._session_tracker.reset(
            self.data.get("ChargeEnergy"), self.data.get("ChargeTime")
        )
        await self._async_save_session()
        self.async_set_updated_data(
            {
                **self.data,
                SESSION_ENERGY_KEY: self._session_tracker.energy,
                SESSION_ACTIVE_TIME_KEY: self._session_tracker.active_time,
            }
        )

    async def async_save_session_state(self) -> None:
        """Save the latest checkpoint during a clean config-entry unload."""
        await self._async_save_session()

    async def _async_save_session(self) -> None:
        """Persist the small session checkpoint without using the recorder."""
        await self._session_store.async_save(self._session_tracker.state.as_dict())
        self._last_session_save = monotonic()
