"""Pure scheduling and real async controller tests; no charger is contacted."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from custom_components.v2c_trydan.scheduling.controller import SchedulingController
from custom_components.v2c_trydan.scheduling.policy import (
    DAYS,
    ChargingPolicy,
    SchedulerState,
    WeeklySchedule,
)

MONDAY = datetime(2026, 11, 2, 7, 0)


def block(days=None, start="00:00", end="08:00", period="off_peak"):
    return {"days": days or list(DAYS), "start": start, "end": end, "period": period}


def schedule(blocks=None, enabled=True, allowed=None):
    return WeeklySchedule.from_options(
        {
            "enabled": enabled,
            "allowed": ["off_peak"] if allowed is None else allowed,
            "blocks": [block()] if blocks is None else blocks,
        }
    )


def snapshot(**changes):
    return {"ChargeState": 2, "Paused": 0, "Locked": 0, "Timer": 0, **changes}


@pytest.mark.parametrize(
    "minute,period",
    [(0, "off_peak"), (479, "off_peak"), (480, "unassigned"), (1439, "unassigned")],
)
def test_exact_block_boundaries(minute, period):
    assert (
        schedule().period_at(MONDAY.replace(hour=0) + timedelta(minutes=minute))
        == period
    )


def test_overnight_sunday_wraps_into_monday():
    configured = schedule([block(["sun"], "22:00", "06:00")])
    assert configured.period_at(MONDAY.replace(hour=5)) == "off_peak"
    assert configured.period_at(MONDAY.replace(hour=6)) == "unassigned"


def test_full_day_and_adjacent_tariffs():
    configured = schedule(
        [
            block(["mon"], "00:00", "08:00"),
            block(["mon"], "08:00", "10:00", "shoulder"),
            block(["sat"], "00:00", "00:00"),
        ]
    )
    assert configured.period_at(MONDAY.replace(hour=8)) == "shoulder"
    assert configured.period_at(MONDAY + timedelta(days=5, hours=14)) == "off_peak"


@pytest.mark.parametrize(
    "blocks",
    [
        [block(), block()],
        [block(["sun"], "23:00", "07:00"), block(["mon"], "06:00", "08:00")],
        [block(start="08:00", end="08:00")],
        [block(start="25:00")],
        [block(start="12:99")],
        [block(start="1:00")],
        [block(start="00:00:01")],
        [{**block(), "days": []}],
        [block(["mon", "mon"])],
        [block(["holiday"])],
        [block(period="cheap")],
        [None],
    ],
)
def test_invalid_blocks_are_rejected(blocks):
    with pytest.raises(ValueError):
        schedule(blocks)


@pytest.mark.parametrize(
    "raw",
    [
        False,
        [],
        {"enabled": "false"},
        {"allowed": "off_peak"},
        {"allowed": ["unknown"]},
        {"blocks": {}},
    ],
)
def test_invalid_configuration_never_becomes_permission(raw):
    with pytest.raises(ValueError):
        WeeklySchedule.from_options(raw)


def test_disabled_is_noop_and_initial_mode_is_paused():
    assert (
        ChargingPolicy(schedule(enabled=False)).evaluate(MONDAY, snapshot()).pause
        is None
    )
    assert ChargingPolicy(schedule()).evaluate(MONDAY, snapshot()).pause is True


@pytest.mark.parametrize(
    "mode,hour,target",
    [
        ("automatic", 7, None),
        ("automatic", 9, True),
        ("charge_now", 9, None),
        ("paused", 7, True),
    ],
)
def test_modes_and_tariff_selection(mode, hour, target):
    policy = ChargingPolicy(schedule(), SchedulerState(mode=mode))
    assert policy.evaluate(MONDAY.replace(hour=hour), snapshot()).pause is target


def test_no_selected_tariff_pauses_even_inside_a_block():
    policy = ChargingPolicy(schedule(allowed=[]), SchedulerState(mode="automatic"))
    assert policy.evaluate(MONDAY, snapshot()).pause is True


@pytest.mark.parametrize(
    "data,reason",
    [
        (None, "unavailable"),
        (snapshot(ChargeState=3), "charger_fault"),
        (snapshot(ChargeState=6), "charger_fault"),
        (snapshot(Locked=1), "locked"),
        (snapshot(Timer=1), "device_timer"),
        (snapshot(Paused=None), "incomplete_data"),
    ],
)
def test_unavailable_fault_and_safety_states_never_resume(data, reason):
    policy = ChargingPolicy(schedule(), SchedulerState(mode="charge_now"))
    result = policy.evaluate(MONDAY, data)
    assert result.reason == reason
    assert result.pause is None
    assert policy.state.mode == "charge_now"


def test_force_survives_pause_restart_fault_and_network_loss_until_unplugged():
    policy = ChargingPolicy(schedule())
    policy.set_mode("charge_now", snapshot())
    for data in [snapshot(ChargeState=1), None, snapshot(ChargeState=4)]:
        policy.evaluate(MONDAY, data)
    restored = ChargingPolicy(
        schedule(), SchedulerState.from_dict(policy.state.as_dict())
    )
    assert restored.state.mode == "charge_now"
    restored.evaluate(MONDAY, snapshot(ChargeState=0))
    assert restored.state.mode == "automatic"


def test_force_can_be_armed_before_connecting():
    policy = ChargingPolicy(schedule())
    policy.set_mode("charge_now", snapshot(ChargeState=0))
    policy.evaluate(MONDAY, snapshot(ChargeState=0))
    assert policy.state.mode == "charge_now"
    policy.evaluate(MONDAY, snapshot())
    policy.evaluate(MONDAY, snapshot(ChargeState=0))
    assert policy.state.mode == "automatic"


def test_external_pause_latches_until_an_explicit_mode_selection():
    policy = ChargingPolicy(schedule(), SchedulerState(mode="automatic"))
    policy.evaluate(MONDAY, snapshot())
    result = policy.evaluate(MONDAY, snapshot(Paused=1))
    assert policy.state.mode == "paused"
    assert result.reason == "manual_pause"
    policy.set_mode("automatic", snapshot(Paused=1))
    assert policy.evaluate(MONDAY, snapshot(Paused=1)).pause is False


def test_unplug_does_not_erase_evidence_of_a_new_external_pause():
    policy = ChargingPolicy(schedule(), SchedulerState(mode="automatic"))
    policy.evaluate(MONDAY, snapshot())
    policy.evaluate(MONDAY, snapshot(ChargeState=0))
    policy.evaluate(MONDAY, snapshot(Paused=1))
    assert policy.state.mode == "paused"


def test_repeated_local_hour_uses_wall_clock_not_utc():
    for offset in [1, 2]:
        local = MONDAY.replace(hour=2, tzinfo=timezone(timedelta(hours=offset)))
        assert schedule().period_at(local) == "off_peak"


@pytest.mark.parametrize("raw", [None, [], {"mode": "invalid"}])
def test_invalid_checkpoint_starts_paused(raw):
    assert SchedulerState.from_dict(raw).mode == "paused"


@pytest.fixture
def runtime():
    data = snapshot(Paused=1)
    writes = []
    saves = []

    async def write(pause):
        writes.append(pause)
        data["Paused"] = int(pause)

    async def save(state):
        saves.append(state.copy())

    controller = SchedulingController(
        ChargingPolicy(schedule()),
        lambda: data,
        write,
        save,
        AsyncMock(),
        lambda: MONDAY,
    )
    return controller, data, writes, saves


async def test_controller_checkpoints_then_writes_once_and_confirms(runtime):
    controller, _data, writes, saves = runtime
    await controller.async_evaluate("automatic")
    assert writes == [False]
    assert any(state["pending_pause"] is False for state in saves)
    assert saves[-1]["pending_pause"] is None
    assert controller.decision.reason == "charging_allowed"
    await controller.async_evaluate()
    assert writes == [False]


async def test_lost_ack_is_not_blindly_retried_even_after_restart(runtime):
    controller, data, _writes, saves = runtime
    controller.write_pause = AsyncMock(side_effect=TimeoutError)
    with pytest.raises(TimeoutError):
        await controller.async_evaluate("automatic")
    controller.restore(SchedulerState.from_dict(saves[-1]))
    await controller.async_evaluate()
    controller.write_pause.assert_awaited_once()
    assert controller.decision.reason == "command_unconfirmed"
    data["Paused"] = 0
    await controller.async_evaluate()
    assert controller.decision.reason == "charging_allowed"


async def test_failed_checkpoint_prevents_any_command(runtime):
    controller, _data, writes, _saves = runtime
    controller.save = AsyncMock(side_effect=OSError)
    with pytest.raises(OSError):
        await controller.async_evaluate("automatic")
    assert writes == []


async def test_concurrent_updates_do_not_duplicate_commands(runtime):
    controller, _data, writes, _saves = runtime
    await asyncio.gather(
        controller.async_evaluate("automatic"), controller.async_evaluate()
    )
    assert writes == [False]


async def test_cancellation_keeps_pending_intent_for_reconciliation(runtime):
    controller, _data, _writes, saves = runtime
    controller.write_pause = AsyncMock(side_effect=asyncio.CancelledError)
    with pytest.raises(asyncio.CancelledError):
        await controller.async_evaluate("automatic")
    assert saves[-1]["pending_pause"] is False
    await controller.async_evaluate()
    controller.write_pause.assert_awaited_once()


async def test_stop_during_checkpoint_cannot_send_a_late_command(runtime):
    controller, _data, writes, _saves = runtime

    async def stop_on_save(state):
        controller.stop()

    controller.save = stop_on_save
    await controller.async_evaluate("automatic")
    await controller.async_evaluate("charge_now")
    assert writes == []
