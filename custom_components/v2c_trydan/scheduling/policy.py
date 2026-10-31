"""Pure weekly tariff configuration and persistent scheduling decisions.

Times are local wall-clock minutes. No tariff hours or holidays are assumed.
Unassigned time is denied, and overlaps (including across midnight) are invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from itertools import pairwise
from typing import Any

from ..utils import cable_connected_from_charge_state, value_as_bool

PERIODS = ("peak", "shoulder", "off_peak")
MODES = ("automatic", "charge_now", "paused")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
OPTION_KEY = "scheduling"


def _minute(value: str) -> int:
    """Accept time-selector output, rejecting seconds and malformed times."""
    if not isinstance(value, str):
        raise ValueError("Invalid time")
    parts = value.split(":")
    if len(parts) not in (2, 3) or any(len(part) != 2 for part in parts):
        raise ValueError("Invalid time")
    if not all(part.isascii() and part.isdigit() for part in parts):
        raise ValueError("Invalid time")
    hour, minute = int(parts[0]), int(parts[1])
    if hour > 23 or minute > 59 or (len(parts) == 3 and parts[2] != "00"):
        raise ValueError("Invalid time")
    return hour * 60 + minute


@dataclass(frozen=True)
class WeeklySchedule:
    """Validated, non-overlapping intervals in a 10080-minute week."""

    enabled: bool = False
    allowed: frozenset[str] = frozenset({"off_peak"})
    intervals: tuple[tuple[int, int, str], ...] = ()

    @classmethod
    def from_options(cls, raw: Any) -> WeeklySchedule:
        """Validate persisted configuration; never turn invalid input into allow."""
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise ValueError("Invalid scheduling configuration")
        enabled = raw.get("enabled", False)
        allowed = raw.get("allowed", ["off_peak"])
        blocks = raw.get("blocks", [])
        if (
            not isinstance(enabled, bool)
            or not isinstance(allowed, list)
            or any(period not in PERIODS for period in allowed)
            or not isinstance(blocks, list)
            or len(blocks) > 100
        ):
            raise ValueError("Invalid scheduling configuration")
        intervals: list[tuple[int, int, str]] = []
        for block in blocks:
            if not isinstance(block, dict):
                raise ValueError("Invalid block")
            days = block.get("days")
            period = block.get("period")
            if (
                not isinstance(days, list)
                or not days
                or any(day not in DAYS for day in days)
                or len(set(days)) != len(days)
                or period not in PERIODS
            ):
                raise ValueError("Invalid block")
            start, end = _minute(block.get("start")), _minute(block.get("end"))
            if start == end and start != 0:
                raise ValueError("Only midnight to midnight means a full day")
            duration = (end - start) % 1440 or 1440
            for day in days:
                beginning = DAYS.index(day) * 1440 + start
                finish = beginning + duration
                intervals.append((beginning, min(finish, 10080), period))
                if finish > 10080:
                    intervals.append((0, finish - 10080, period))
        intervals.sort()
        if any(a[1] > b[0] for a, b in pairwise(intervals)):
            raise ValueError("Overlapping blocks")
        return cls(enabled, frozenset(allowed), tuple(intervals))

    def period_at(self, now: datetime) -> str:
        """Use HA's local date/time, including its current UTC offset."""
        minute = now.weekday() * 1440 + now.hour * 60 + now.minute
        return next(
            (period for start, end, period in self.intervals if start <= minute < end),
            "unassigned",
        )


@dataclass
class SchedulerState:
    """User intent and command reconciliation, independent of session energy."""

    mode: str = "paused"
    force_connected: bool = False
    last_paused: bool | None = None
    pending_pause: bool | None = None

    @classmethod
    def from_dict(cls, raw: Any) -> SchedulerState:
        """Restore conservatively, without allowing malformed state to resume."""
        if not isinstance(raw, dict) or raw.get("mode") not in MODES:
            return cls()
        return cls(
            mode=raw["mode"],
            force_connected=raw.get("force_connected") is True,
            last_paused=raw.get("last_paused")
            if isinstance(raw.get("last_paused"), bool)
            else None,
            pending_pause=raw.get("pending_pause")
            if isinstance(raw.get("pending_pause"), bool)
            else None,
        )

    def as_dict(self) -> dict[str, Any]:
        return vars(self).copy()


@dataclass(frozen=True)
class Decision:
    period: str
    reason: str
    pause: bool | None = None


@dataclass
class ChargingPolicy:
    """Decide only; the controller owns writes, ordering and persistence."""

    schedule: WeeklySchedule
    state: SchedulerState = field(default_factory=SchedulerState)

    def set_mode(self, mode: str, data: dict[str, Any] | None) -> None:
        if mode not in MODES:
            raise ValueError("Unsupported scheduling mode")
        self.state.mode = mode
        self.state.pending_pause = None
        self.state.last_paused = value_as_bool(data.get("Paused")) if data else None
        self.state.force_connected = bool(
            mode == "charge_now"
            and data
            and cable_connected_from_charge_state(data.get("ChargeState")) is True
        )

    def evaluate(self, now: datetime, data: dict[str, Any] | None) -> Decision:
        period = self.schedule.period_at(now)
        if not self.schedule.enabled:
            return Decision(period, "disabled")
        if data is None:
            return Decision(period, "unavailable")
        connected = cable_connected_from_charge_state(data.get("ChargeState"))
        if connected is False:
            if self.state.mode == "charge_now" and self.state.force_connected:
                self.state.mode = "automatic"
                self.state.force_connected = False
            return Decision(period, "disconnected")
        if connected is None:
            return Decision(period, "charger_fault")
        if self.state.mode == "charge_now":
            self.state.force_connected = True
        paused = value_as_bool(data.get("Paused"))
        locked = value_as_bool(data.get("Locked"))
        timer = value_as_bool(data.get("Timer"))
        if paused is None or locked is None or timer is None:
            return Decision(period, "incomplete_data")
        if self.state.pending_pause is not None:
            if paused != self.state.pending_pause:
                return Decision(period, "command_unconfirmed")
            self.state.pending_pause = None
        elif paused and self.state.last_paused is False:
            # A new pause not requested by us is a manual/external stop. Latch
            # Paused until the user explicitly chooses Auto or Charge now.
            self.state.mode = "paused"
        self.state.last_paused = paused
        if locked:
            return Decision(period, "locked")
        if timer:
            return Decision(period, "device_timer")
        desired_pause = self.state.mode == "paused" or (
            self.state.mode == "automatic" and period not in self.schedule.allowed
        )
        reason = (
            "manual_pause"
            if self.state.mode == "paused"
            else "charge_now"
            if self.state.mode == "charge_now"
            else "waiting_schedule"
            if desired_pause
            else "charging_allowed"
        )
        return Decision(
            period, reason, desired_pause if desired_pause != paused else None
        )
