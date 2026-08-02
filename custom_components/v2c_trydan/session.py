"""Track energy across charger counter resets within one cable session.

The Trydan ``ChargeEnergy`` value may restart when an external controller pauses
and resumes charging.  This module deliberately has no Home Assistant imports so
the accumulation rules remain small, deterministic, and easy to unit test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .utils import value_as_float, value_as_int


@dataclass(slots=True)
class SessionEnergyState:
    """Serializable state required to continue an interrupted HA session."""

    energy: float = 0.0
    last_raw_energy: float | None = None
    cable_connected: bool | None = None

    @classmethod
    def from_dict(cls, data: object) -> SessionEnergyState:
        """Build state from untrusted persisted data, ignoring invalid values."""
        if not isinstance(data, dict):
            return cls()

        energy = value_as_float(data.get("energy"))
        last_raw_energy = value_as_float(data.get("last_raw_energy"))
        cable_connected = data.get("cable_connected")
        return cls(
            energy=max(energy or 0.0, 0.0),
            last_raw_energy=(
                max(last_raw_energy, 0.0) if last_raw_energy is not None else None
            ),
            cable_connected=(
                cable_connected if isinstance(cable_connected, bool) else None
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SessionEnergyUpdate:
    """Describe whether an update requires persistence or immediate saving."""

    changed: bool
    connection_changed: bool


class SessionEnergyTracker:
    """Accumulate all charging segments until a new cable connection starts."""

    def __init__(self, state: SessionEnergyState | None = None) -> None:
        """Initialize from optional persisted state."""
        self.state = state or SessionEnergyState()

    @property
    def energy(self) -> float:
        """Return accumulated session energy in kWh."""
        return self.state.energy

    def update(self, charge_state: object, raw_energy: object) -> SessionEnergyUpdate:
        """Consume one charger snapshot and accumulate non-negative deltas.

        Charge states 1 and 2 mean the cable is connected. A transition from
        disconnected to connected starts a new session. While connected, a raw
        counter decrease is interpreted as an external pause/reset and the new
        counter value becomes the first contribution of the next segment.
        """
        parsed_charge_state = value_as_int(charge_state)
        connected = (
            parsed_charge_state in (1, 2) if parsed_charge_state is not None else None
        )
        current_raw = value_as_float(raw_energy)
        if current_raw is not None:
            current_raw = max(current_raw, 0.0)

        previous_connected = self.state.cable_connected
        connection_changed = (
            connected is not None and connected != previous_connected
        )
        previous = self.state.as_dict()

        if connected is True and previous_connected is False:
            # Do not inherit a stale counter from the previously unplugged car.
            previous_raw = self.state.last_raw_energy
            self.state.energy = (
                current_raw
                if current_raw is not None
                and (
                    previous_raw is None
                    or previous_raw == 0
                    or current_raw < previous_raw
                )
                else 0.0
            )
            self.state.last_raw_energy = current_raw
        elif connected is True and current_raw is not None:
            last_raw = self.state.last_raw_energy
            if last_raw is None:
                # On first installation or after invalid persisted data, retaining
                # the current segment is more useful than reporting a false zero.
                self.state.energy += current_raw
            elif current_raw >= last_raw:
                self.state.energy += current_raw - last_raw
            else:
                # The charger restarted its segment counter after an OCPP/app pause.
                self.state.energy += current_raw
            self.state.last_raw_energy = current_raw
        elif connected is False and previous_connected is True:
            # Keep the finished total visible until the next cable connection.
            last_raw = self.state.last_raw_energy
            if (
                current_raw is not None
                and last_raw is not None
                and current_raw >= last_raw
            ):
                self.state.energy += current_raw - last_raw
            if current_raw is not None:
                self.state.last_raw_energy = current_raw
        elif connected is False and current_raw is not None:
            # Track firmware changes while unplugged as the baseline for deciding
            # whether the first connected reading is stale or already new energy.
            self.state.last_raw_energy = current_raw

        if connected is not None:
            self.state.cable_connected = connected

        return SessionEnergyUpdate(
            changed=self.state.as_dict() != previous,
            connection_changed=connection_changed,
        )

    def reset(self, raw_energy: object = None) -> None:
        """Reset the total while treating the current raw value as the baseline."""
        current_raw = value_as_float(raw_energy)
        self.state.energy = 0.0
        self.state.last_raw_energy = (
            max(current_raw, 0.0) if current_raw is not None else None
        )
