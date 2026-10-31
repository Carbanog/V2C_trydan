"""Home Assistant lifecycle adapter for the optional scheduling controller."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..api import V2CTrydanError
from ..const import DOMAIN
from .controller import SchedulingController
from .policy import ChargingPolicy, SchedulerState, WeeklySchedule

if TYPE_CHECKING:
    from ..coordinator import V2CTrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


def store_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}.scheduling"


class SchedulingManager:
    """Own subscriptions/tasks; the charger coordinator remains read-only here."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: V2CTrydanDataUpdateCoordinator,
        schedule: WeeklySchedule,
    ) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(
            hass, STORE_VERSION, store_key(entry.entry_id), atomic_writes=True
        )
        self.controller = SchedulingController(
            ChargingPolicy(schedule),
            self._snapshot,
            self._write_pause,
            self._store.async_save,
            coordinator.async_request_refresh,
            dt_util.now,
        )
        self._listeners: set[Callable[[], None]] = set()
        self._unsubscribers: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None
        self._dirty = False
        self._stopped = False

    async def async_initialize(self) -> None:
        self.controller.restore(
            SchedulerState.from_dict(await self._store.async_load())
        )

    async def async_start(self) -> None:
        self._unsubscribers = [
            self.coordinator.async_add_listener(self._request_evaluation),
            async_track_time_change(self.hass, self._request_evaluation, second=0),
        ]
        self._request_evaluation()

    def _snapshot(self) -> dict[str, Any] | None:
        if not self.coordinator.last_update_success:
            return None
        return self.coordinator.data

    async def _write_pause(self, pause: bool) -> None:
        await self.coordinator.api.async_write("Paused", int(pause))

    @callback
    def _request_evaluation(self, *_: Any) -> None:
        if self._stopped:
            return
        self._dirty = True
        if self._task is None or self._task.done():
            self._task = self.hass.async_create_task(self._async_run())

    async def _async_run(self) -> None:
        while self._dirty and not self._stopped:
            self._dirty = False
            try:
                await self.controller.async_evaluate()
            except V2CTrydanError:
                # The checkpoint retains the pending command. Do not repeatedly
                # write or log the same failure on every data/clock notification.
                _LOGGER.warning(
                    "Scheduled pause/resume was not confirmed; review scheduler status"
                )
            finally:
                self._notify()

    async def async_set_mode(self, mode: str) -> None:
        """An explicit action may retry a previously unconfirmed intent."""
        try:
            await self.controller.async_evaluate(mode)
        finally:
            self._notify()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    @callback
    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    async def async_stop(self) -> None:
        """Unload without resuming a charger that may have been paused manually."""
        self._stopped = True
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._listeners.clear()
