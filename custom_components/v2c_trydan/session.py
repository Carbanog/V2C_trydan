"""Track charger counters across resets within one cable session.

Trydan may restart ``ChargeEnergy`` and ``ChargeTime`` whenever an external
controller pauses and resumes charging. This module has no Home Assistant
imports so the accumulation rules remain deterministic and easy to test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .utils import value_as_float, value_as_int


@dataclass(slots=True)
class SessionState:
    """Serializable state needed to resume session statistics after restart."""

    energy: float = 0.0
    active_time: float = 0.0
    last_raw_energy: float | None = None
    last_raw_time: float | None = None
    cable_connected: bool | None = None

    @classmethod
    def from_dict(cls, data: object) -> SessionState:
        """Build state from untrusted storage, including the b4 energy schema."""
        if not isinstance(data, dict):
            return cls()

        cable_connected = data.get("cable_connected")
        return cls(
            energy=_non_negative(data.get("energy")) or 0.0,
            active_time=_non_negative(data.get("active_time")) or 0.0,
            last_raw_energy=_non_negative(data.get("last_raw_energy")),
            last_raw_time=_non_negative(data.get("last_raw_time")),
            cable_connected=(
                cable_connected if isinstance(cable_connected, bool) else None
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SessionUpdate:
    """Describe whether an update needs persistence or an immediate save."""

    changed: bool
    connection_changed: bool


class SessionTracker:
    """Accumulate energy and active time until a new cable session starts."""

    def __init__(self, state: SessionState | None = None) -> None:
        """Initialize from optional persisted state."""
        self.state = state or SessionState()

    @property
    def energy(self) -> float:
        """Return accumulated session energy in kWh."""
        return self.state.energy

    @property
    def active_time(self) -> float:
        """Return accumulated active charging time in seconds."""
        return self.state.active_time

    def update(
        self,
        charge_state: object,
        raw_energy: object,
        raw_time: object,
    ) -> SessionUpdate:
        """Consume one charger snapshot and accumulate non-negative deltas.

        Charge states 1 and 2 mean the cable is connected. A transition from
        disconnected to connected starts a new session. While connected, a raw
        counter decrease starts a new segment without discarding earlier ones.
        """
        parsed_charge_state = value_as_int(charge_state)
        connected = (
            parsed_charge_state in (1, 2) if parsed_charge_state is not None else None
        )
        current_energy = _non_negative(raw_energy)
        current_time = _non_negative(raw_time)
        previous_connected = self.state.cable_connected
        connection_changed = connected is not None and connected != previous_connected
        previous = self.state.as_dict()

        if connected is True and previous_connected is False:
            self.state.energy = _new_session_value(
                current_energy, self.state.last_raw_energy
            )
            self.state.active_time = _new_session_value(
                current_time, self.state.last_raw_time
            )
        elif connected is True:
            self.state.energy = _accumulate_counter(
                self.state.energy, current_energy, self.state.last_raw_energy
            )
            self.state.active_time = _accumulate_counter(
                self.state.active_time, current_time, self.state.last_raw_time
            )
        elif connected is False and previous_connected is True:
            # Include a final monotonic delta and retain the completed totals.
            self.state.energy = _final_counter_delta(
                self.state.energy, current_energy, self.state.last_raw_energy
            )
            self.state.active_time = _final_counter_delta(
                self.state.active_time, current_time, self.state.last_raw_time
            )

        if current_energy is not None:
            self.state.last_raw_energy = current_energy
        if current_time is not None:
            self.state.last_raw_time = current_time
        if connected is not None:
            self.state.cable_connected = connected

        return SessionUpdate(
            changed=self.state.as_dict() != previous,
            connection_changed=connection_changed,
        )

    def reset(self, raw_energy: object = None, raw_time: object = None) -> None:
        """Reset totals while treating current counters as new baselines."""
        self.state.energy = 0.0
        self.state.active_time = 0.0
        self.state.last_raw_energy = _non_negative(raw_energy)
        self.state.last_raw_time = _non_negative(raw_time)


def _non_negative(value: object) -> float | None:
    """Convert a finite numeric value and reject negative counter values."""
    converted = value_as_float(value)
    if converted is None or converted < 0:
        return None
    return converted


def _new_session_value(current: float | None, previous: float | None) -> float:
    """Use an already advancing counter without inheriting a stale segment."""
    if current is None:
        return 0.0
    if previous is None or previous == 0 or current < previous:
        return current
    return 0.0


def _accumulate_counter(
    total: float, current: float | None, previous: float | None
) -> float:
    """Add a monotonic delta or the first value after a counter reset."""
    if current is None:
        return total
    if previous is None:
        return total + current
    return total + (current - previous if current >= previous else current)


def _final_counter_delta(
    total: float, current: float | None, previous: float | None
) -> float:
    """Add only a final monotonic delta when the cable is disconnected."""
    if current is None or previous is None or current < previous:
        return total
    return total + current - previous
