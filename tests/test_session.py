"""Tests for charging-session energy accumulation."""

from __future__ import annotations

import pytest

from custom_components.v2c_trydan.session import (
    SessionEnergyState,
    SessionEnergyTracker,
)


def test_accumulates_counter_resets_until_next_connection() -> None:
    """OCPP pauses may reset raw energy without ending the cable session."""
    tracker = SessionEnergyTracker()

    tracker.update(0, 0)
    tracker.update(1, 0)
    tracker.update(2, 1.2)
    tracker.update(1, 1.2)
    tracker.update(2, 0.4)
    tracker.update(2, 1.0)
    tracker.update(0, 0)

    assert tracker.energy == pytest.approx(2.2)


def test_finished_total_remains_until_next_cable_connection() -> None:
    """A delayed disconnect automation must still see the completed total."""
    tracker = SessionEnergyTracker()
    tracker.update(0, 0)
    tracker.update(1, 0)
    tracker.update(2, 3.4)
    tracker.update(0, 3.5)

    assert tracker.energy == pytest.approx(3.5)

    tracker.update(1, 0)
    assert tracker.energy == 0


def test_first_connected_reading_keeps_energy_if_counter_already_advanced() -> None:
    """A poll interval must not discard energy delivered just after plugging in."""
    tracker = SessionEnergyTracker()
    tracker.update(0, 0)

    tracker.update(2, 0.2)

    assert tracker.energy == pytest.approx(0.2)


def test_new_connection_does_not_inherit_stale_disconnected_counter() -> None:
    """Firmware retaining the previous raw value must still start at zero."""
    tracker = SessionEnergyTracker()
    tracker.update(0, 3.5)

    tracker.update(1, 3.5)

    assert tracker.energy == 0


def test_restored_connected_session_continues_after_restart() -> None:
    """Persisted baselines prevent double counting across HA restarts."""
    restored = SessionEnergyState(
        energy=2.5,
        last_raw_energy=1.0,
        cable_connected=True,
    )
    tracker = SessionEnergyTracker(restored)

    tracker.update(2, 1.4)

    assert tracker.energy == pytest.approx(2.9)


def test_manual_reset_uses_current_counter_as_new_baseline() -> None:
    """Resetting during a charge must not immediately restore old energy."""
    tracker = SessionEnergyTracker()
    tracker.update(2, 2.0)

    tracker.reset(2.0)
    tracker.update(2, 2.5)

    assert tracker.energy == pytest.approx(0.5)


def test_invalid_persisted_state_is_safely_ignored() -> None:
    """Corrupt storage cannot create negative or non-numeric energy."""
    state = SessionEnergyState.from_dict(
        {"energy": -3, "last_raw_energy": "bad", "cable_connected": "yes"}
    )

    assert state == SessionEnergyState()
