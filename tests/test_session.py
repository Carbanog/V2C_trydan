"""Tests for charging-session statistics accumulation."""

from __future__ import annotations

import pytest

from custom_components.v2c_trydan.session import SessionState, SessionTracker


def test_accumulates_counter_resets_until_next_connection() -> None:
    """OCPP pauses may reset both raw counters without ending the session."""
    tracker = SessionTracker()

    tracker.update(0, 0, 0)
    tracker.update(1, 0, 0)
    tracker.update(2, 1.2, 600)
    tracker.update(1, 1.2, 600)
    tracker.update(2, 0.4, 120)
    tracker.update(2, 1.0, 420)
    tracker.update(0, 0, 0)

    assert tracker.energy == pytest.approx(2.2)
    assert tracker.active_time == pytest.approx(1020)


def test_finished_totals_remain_until_next_cable_connection() -> None:
    """A delayed disconnect automation must still see completed statistics."""
    tracker = SessionTracker()
    tracker.update(0, 0, 0)
    tracker.update(1, 0, 0)
    tracker.update(2, 3.4, 900)
    tracker.update(0, 3.5, 930)

    assert tracker.energy == pytest.approx(3.5)
    assert tracker.active_time == pytest.approx(930)

    tracker.update(1, 0, 0)
    assert tracker.energy == 0
    assert tracker.active_time == 0


def test_first_connected_reading_keeps_already_advanced_counters() -> None:
    """A poll interval must not discard delivery just after plugging in."""
    tracker = SessionTracker()
    tracker.update(0, 0, 0)

    tracker.update(2, 0.2, 30)

    assert tracker.energy == pytest.approx(0.2)
    assert tracker.active_time == pytest.approx(30)


def test_new_connection_does_not_inherit_stale_disconnected_counters() -> None:
    """Firmware retaining previous values must still start at zero."""
    tracker = SessionTracker()
    tracker.update(0, 3.5, 930)

    tracker.update(1, 3.5, 930)

    assert tracker.energy == 0
    assert tracker.active_time == 0


def test_b4_energy_checkpoint_migrates_and_time_starts_safely() -> None:
    """The additive schema must retain energy saved by beta 4."""
    state = SessionState.from_dict(
        {"energy": 2.5, "last_raw_energy": 1.0, "cable_connected": True}
    )
    tracker = SessionTracker(state)

    tracker.update(2, 1.4, 120)

    assert tracker.energy == pytest.approx(2.9)
    assert tracker.active_time == pytest.approx(120)


def test_restored_session_continues_both_counters_after_restart() -> None:
    """Persisted baselines prevent double counting across HA restarts."""
    tracker = SessionTracker(
        SessionState(
            energy=2.5,
            active_time=600,
            last_raw_energy=1.0,
            last_raw_time=300,
            cable_connected=True,
        )
    )

    tracker.update(2, 1.4, 420)

    assert tracker.energy == pytest.approx(2.9)
    assert tracker.active_time == pytest.approx(720)


def test_manual_reset_uses_current_counters_as_new_baselines() -> None:
    """Resetting during charge must not immediately restore old totals."""
    tracker = SessionTracker()
    tracker.update(2, 2.0, 400)

    tracker.reset(2.0, 400)
    tracker.update(2, 2.5, 460)

    assert tracker.energy == pytest.approx(0.5)
    assert tracker.active_time == pytest.approx(60)


def test_invalid_persisted_state_is_safely_ignored() -> None:
    """Corrupt storage cannot create invalid statistics."""
    state = SessionState.from_dict(
        {
            "energy": -3,
            "active_time": "bad",
            "last_raw_energy": "bad",
            "last_raw_time": -2,
            "cable_connected": "yes",
        }
    )

    assert state == SessionState()
