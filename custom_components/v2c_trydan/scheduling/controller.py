"""Serialized scheduling side effects, testable without Home Assistant."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from .policy import ChargingPolicy, Decision, SchedulerState


class SchedulingController:
    """Checkpoint intent before sending a single pause/resume command.

    An acknowledgement can be lost after execution. Pending intent therefore
    survives exceptions/restarts and is reconciled with a fresh read, never
    blindly retried. An explicit user mode selection can clear an unresolved
    command, after the user has reviewed the charger state.
    """

    def __init__(
        self,
        policy: ChargingPolicy,
        snapshot: Callable[[], dict[str, Any] | None],
        write_pause: Callable[[bool], Awaitable[None]],
        save: Callable[[dict[str, Any]], Awaitable[None]],
        refresh: Callable[[], Awaitable[None]],
        now: Callable[[], datetime],
    ) -> None:
        self.policy = policy
        self.snapshot = snapshot
        self.write_pause = write_pause
        self.save = save
        self.refresh = refresh
        self.now = now
        self.decision = Decision("unassigned", "unavailable")
        self._lock = asyncio.Lock()
        self._saved = policy.state.as_dict()
        self._active = True

    def stop(self) -> None:
        """Reject queued work; a command already sent cannot be recalled."""
        self._active = False

    def restore(self, state: SchedulerState) -> None:
        """Restore only before listeners start or commands can be scheduled."""
        self.policy.state = state
        self._saved = state.as_dict()

    async def async_evaluate(self, mode: str | None = None) -> None:
        """Serialize user actions and clock/data updates on the same policy."""
        async with self._lock:
            if not self._active:
                return
            if mode is not None:
                self.policy.set_mode(mode, self.snapshot())
            self.decision = self.policy.evaluate(self.now(), self.snapshot())
            await self._async_save_if_changed()
            if self.decision.pause is None or not self._active:
                return
            pause = self.decision.pause
            self.policy.state.pending_pause = pause
            await self._async_save_if_changed()
            if not self._active:
                return
            # Keep the pending checkpoint on any write failure or cancellation.
            # A follow-up read may still prove that the command was applied.
            try:
                await self.write_pause(pause)
            finally:
                self.decision = Decision(self.decision.period, "command_unconfirmed")
            if not self._active:
                return
            await self.refresh()
            self.decision = self.policy.evaluate(self.now(), self.snapshot())
            await self._async_save_if_changed()

    async def _async_save_if_changed(self) -> None:
        state = self.policy.state.as_dict()
        if state != self._saved:
            await self.save(state)
            self._saved = state
