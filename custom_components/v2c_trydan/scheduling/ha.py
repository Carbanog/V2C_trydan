"""Home Assistant lifecycle adapter for the optional scheduling controller."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC
from time import monotonic
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..api import V2CTrydanError
from ..const import DOMAIN
from ..utils import cable_connected_from_charge_state
from .alerts import CommandAlert
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
        self._alert = CommandAlert()
        self._issue_id = f"scheduling_{entry.entry_id}_unconfirmed"
        self._charger_name = entry.title
        self.next_allowed_start: str | None = None
        self._next_window_key = None
        self._presentation_lock = asyncio.Lock()

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
                await self._async_update_presentation()
                self._notify()

    async def async_set_mode(self, mode: str) -> None:
        """An explicit action may retry a previously unconfirmed intent."""
        try:
            await self.controller.async_evaluate(mode)
        finally:
            await self._async_update_presentation()
            self._notify()

    async def _async_update_presentation(self) -> None:
        async with self._presentation_lock:
            await self._async_refresh_presentation()

    async def _async_refresh_presentation(self) -> None:
        """No charger IO: debounce alerts and cache a local preview per minute."""
        if self._stopped:
            return
        data = self._snapshot()
        unresolved = self.controller.policy.state.pending_pause is not None and (
            data is None
            or cable_connected_from_charge_state(data.get("ChargeState")) is not False
        )
        action = self._alert.update(unresolved, monotonic())
        if action is True:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="scheduling_command_unconfirmed",
                translation_placeholders={"charger": self._charger_name},
            )
        elif action is False:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)

        policy = self.controller.policy
        now = dt_util.now()
        if (
            policy.state.mode != "automatic"
            or policy.schedule.period_at(now) in policy.schedule.allowed
        ):
            self.next_allowed_start = None
            self._next_window_key = None
            return
        key = (
            now.astimezone(UTC).replace(second=0, microsecond=0),
            str(now.tzinfo),
        )
        if key != self._next_window_key:
            next_start = await self.hass.async_add_executor_job(
                policy.schedule.next_allowed_start, now
            )
            # A user may have changed mode while the executor was searching.
            # Do not publish an Auto preview after a manual pause/override.
            if (
                not self._stopped
                and policy.state.mode == "automatic"
                and policy.schedule.period_at(dt_util.now())
                not in policy.schedule.allowed
            ):
                self.next_allowed_start = next_start.isoformat() if next_start else None
                self._next_window_key = key
            else:
                self.next_allowed_start = None
                self._next_window_key = None

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
        self.controller.stop()
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._listeners.clear()
