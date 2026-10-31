"""Exercise actual HA setup/options/entity/lifecycle code, with a fake charger."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.v2c_trydan.api import V2CTrydanApi, V2CTrydanConnectionError
from custom_components.v2c_trydan.scheduling.policy import WeeklySchedule
from custom_components.v2c_trydan.scheduling.presentation import async_block_choices

DOMAIN = "v2c_trydan"


def options(enabled=True):
    return {
        "scheduling": {
            "enabled": enabled,
            "allowed": ["off_peak"],
            "blocks": [
                {
                    "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                    "start": "00:00",
                    "end": "00:00",
                    "period": "off_peak",
                }
            ],
        }
    }


async def setup_charger(hass, configured):
    data = {
        "ID": "example-charger",
        "FirmwareVersion": "2.5.1",
        "ChargeState": 2,
        "ChargePower": 1000,
        "ChargeEnergy": 1,
        "ChargeTime": 60,
        "Paused": 0,
        "Locked": 0,
        "Timer": 0,
        "Dynamic": 1,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="example-charger",
        data={"ip_address": "192.0.2.10"},
        options=configured,
    )
    entry.add_to_hass(hass)

    async def read():
        return deepcopy(data)

    async def write(key, value):
        assert key == "Paused"
        data[key] = value

    with (
        patch.object(
            V2CTrydanApi,
            "async_get_realtime_data",
            side_effect=read,
        ),
        patch.object(
            V2CTrydanApi,
            "async_write",
            side_effect=write,
        ) as command,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        try:
            yield entry, data, command
        finally:
            if entry.state is ConfigEntryState.LOADED:
                await hass.config_entries.async_unload(entry.entry_id)


async def test_disabled_has_no_scheduler_entities_or_commands(hass):
    async for entry, _data, command in setup_charger(hass, {}):
        assert entry.runtime_data.scheduler is None
        command.assert_not_awaited()
        assert not any(
            "scheduling" in state.entity_id for state in hass.states.async_all()
        )


async def test_enabled_entities_pause_override_and_unload(hass):
    async for entry, data, command in setup_charger(hass, options()):
        manager = entry.runtime_data.scheduler
        assert manager.controller.policy.state.mode == "paused"
        command.assert_awaited_once_with("Paused", 1)
        selects = [
            s
            for s in hass.states.async_all("select")
            if "automatic" in s.attributes.get("options", [])
        ]
        assert len(selects) == 1
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": selects[0].entity_id, "option": "charge_now"},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert data["Paused"] == 0
        # A request_refresh may be debounced. Simulate the next actual poll,
        # then reload to exercise HA Store and subscriptions, not a fake registry.
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert manager._stopped
        manager = entry.runtime_data.scheduler
        assert manager.controller.policy.state.mode == "charge_now"
        data["ChargeState"] = 0
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert entry.runtime_data.data["ChargeState"] == 0
        assert manager.controller.policy.state.mode == "automatic"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert manager._stopped
        assert not manager._unsubscribers


async def test_options_flow_edits_draft_and_preserves_other_options(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options={"unrelated": "keep"}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "menu"
    flow = result["flow_id"]
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "add_block"}
    )
    assert result["type"] == "form"
    result = await hass.config_entries.options.async_configure(
        flow,
        {"days": ["mon"], "start": "00:00:00", "end": "08:00:00", "period": "off_peak"},
    )
    assert result["type"] == "menu"
    assert "scheduling" not in entry.options
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "save"}
    )
    assert result["type"] == "form"
    assert result["description_placeholders"]["unassigned_minutes"] == "9600"
    assert "scheduling" not in entry.options
    result = await hass.config_entries.options.async_configure(flow, {"confirm": False})
    assert result["errors"] == {"base": "confirm_required"}
    result = await hass.config_entries.options.async_configure(flow, {"confirm": True})
    assert result["type"] == "create_entry"
    assert entry.options["unrelated"] == "keep"
    assert entry.options["scheduling"]["enabled"] is False
    assert len(entry.options["scheduling"]["blocks"]) == 1


async def test_options_reject_overlap_and_allow_adjacent_blocks(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"ip_address": "192.0.2.10"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    flow = result["flow_id"]
    first = {
        "days": ["mon"],
        "start": "00:00:00",
        "end": "08:00:00",
        "period": "off_peak",
    }
    await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "add_block"}
    )
    await hass.config_entries.options.async_configure(flow, first)
    await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "add_block"}
    )
    result = await hass.config_entries.options.async_configure(
        flow, {**first, "start": "07:00:00", "end": "09:00:00"}
    )
    assert result["errors"] == {"base": "invalid_schedule"}
    assert not entry.options
    result = await hass.config_entries.options.async_configure(
        flow, {**first, "start": "08:00:00", "end": "09:00:00"}
    )
    assert result["type"] == "menu"
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "save"}
    )
    assert result["type"] == "form"
    result = await hass.config_entries.options.async_configure(flow, {"confirm": True})
    assert result["type"] == "create_entry"
    assert len(entry.options["scheduling"]["blocks"]) == 2


@pytest.mark.parametrize(
    "language,label", [("en", "Off-peak"), ("es", "Valle"), ("fr", "Heures creuses")]
)
async def test_summary_uses_translations_in_each_supported_language(
    hass, language, label
):
    hass.config.language = language
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=options()
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "save"}
    )
    assert result["type"] == "form"
    assert result["description_placeholders"]["allowed"] == label
    assert result["description_placeholders"]["unassigned_minutes"] == "0"


async def test_persistent_repair_alert_is_deduplicated_and_clears_on_confirmation(hass):
    async for entry, data, _command in setup_charger(hass, options()):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        manager = entry.runtime_data.scheduler
        registry = ir.async_get(hass)
        with (
            patch.object(
                manager.controller,
                "write_pause",
                AsyncMock(side_effect=V2CTrydanConnectionError("test failure")),
            ),
            patch(
                "custom_components.v2c_trydan.scheduling.ha.monotonic", return_value=100
            ) as clock,
            patch.object(
                ir, "async_create_issue", wraps=ir.async_create_issue
            ) as create,
        ):
            with pytest.raises(V2CTrydanConnectionError):
                await manager.async_set_mode("automatic")
            assert registry.async_get_issue(DOMAIN, manager._issue_id) is None
            clock.return_value = 160
            await manager._async_update_presentation()
            assert registry.async_get_issue(DOMAIN, manager._issue_id) is not None
            await manager._async_update_presentation()
            assert create.call_count == 1
            data["Paused"] = 0
            await entry.runtime_data.async_refresh()
            await hass.async_block_till_done()
            assert registry.async_get_issue(DOMAIN, manager._issue_id) is None


@pytest.mark.parametrize(
    "now,start,end,expected",
    [
        (
            datetime(2026, 10, 25, 2, 45, fold=0),
            "01:00",
            "02:30",
            "2026-10-25T02:00:00+01:00",
        ),
        (datetime(2027, 3, 28, 1, 59), "02:30", "03:30", "2027-03-28T03:00:00+02:00"),
        (datetime(2027, 3, 28, 1, 59), "02:00", "02:45", "2027-04-04T02:00:00+02:00"),
    ],
)
def test_preview_handles_real_dst_transitions(now, start, end, expected):
    configured = WeeklySchedule.from_options(
        {
            "enabled": True,
            "allowed": ["off_peak"],
            "blocks": [
                {"days": ["sun"], "start": start, "end": end, "period": "off_peak"}
            ],
        }
    )
    result = configured.next_allowed_start(
        now.replace(tzinfo=ZoneInfo("Europe/Madrid"))
    )
    assert result.isoformat() == expected


async def test_next_window_is_an_attribute_not_a_new_entity(hass):
    configured = options()
    configured["scheduling"]["blocks"][0].update(start="23:00", end="00:00")
    async for entry, _data, _command in setup_charger(hass, configured):
        manager = entry.runtime_data.scheduler
        now = datetime(2026, 11, 2, 12, tzinfo=ZoneInfo("Europe/Madrid"))
        with patch(
            "custom_components.v2c_trydan.scheduling.ha.dt_util.now", return_value=now
        ):
            await manager.async_set_mode("automatic")
        await hass.async_block_till_done()
        status = next(
            s
            for s in hass.states.async_all("sensor")
            if "next_allowed_start" in s.attributes
        )
        assert status.attributes["next_allowed_start"] == "2026-11-02T23:00:00+01:00"


async def start_edit(hass, entry_id, index="0"):
    result = await hass.config_entries.options.async_init(entry_id)
    flow = result["flow_id"]
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "edit_block"}
    )
    assert result["step_id"] == "edit_block"
    result = await hass.config_entries.options.async_configure(flow, {"block": index})
    assert result["step_id"] == "edit_details"
    return flow, result


async def test_edit_prefills_replaces_and_preserves_other_settings(hass):
    configured = options()
    original = {
        "days": ["mon"],
        "start": "00:00:00",
        "end": "08:00:00",
        "period": "off_peak",
    }
    other = {
        "days": ["mon"],
        "start": "08:00:00",
        "end": "10:00:00",
        "period": "shoulder",
    }
    configured["scheduling"]["blocks"] = [original, other]
    configured["unrelated"] = "keep"
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=deepcopy(configured)
    )
    entry.add_to_hass(hass)
    flow, result = await start_edit(hass, entry.entry_id)
    assert {
        key.schema: key.default()
        for key in result["data_schema"].schema
        if key.schema != "navigation"
    } == original
    changed = {
        "days": ["tue"],
        "start": "01:00:00",
        "end": "06:00:00",
        "period": "peak",
    }
    result = await hass.config_entries.options.async_configure(flow, changed)
    assert result["type"] == "menu"
    assert entry.options == configured
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "save"}
    )
    assert result["type"] == "form"
    assert entry.options == configured
    result = await hass.config_entries.options.async_configure(flow, {"confirm": True})
    assert result["type"] == "create_entry"
    assert entry.options["scheduling"]["blocks"] == [changed, other]
    assert entry.options["scheduling"]["enabled"] is True
    assert entry.options["scheduling"]["allowed"] == ["off_peak"]
    assert entry.options["unrelated"] == "keep"


async def test_edit_rejects_overlap_but_not_the_replaced_block_itself(hass):
    configured = options()
    original = {
        "days": ["mon"],
        "start": "00:00:00",
        "end": "08:00:00",
        "period": "off_peak",
    }
    configured["scheduling"]["blocks"] = [
        original,
        {**original, "start": "08:00:00", "end": "10:00:00"},
    ]
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=deepcopy(configured)
    )
    entry.add_to_hass(hass)
    flow, _result = await start_edit(hass, entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        flow, {**original, "end": "09:00:00"}
    )
    assert result["errors"] == {"base": "invalid_schedule"}
    assert entry.options == configured
    result = await hass.config_entries.options.async_configure(flow, original)
    assert result["type"] == "menu"
    hass.config_entries.options.async_abort(flow)
    assert entry.options == configured


async def test_edit_with_no_blocks_returns_to_menu(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"ip_address": "192.0.2.10"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_block"}
    )
    assert result["type"] == "menu"
    assert not entry.options


@pytest.mark.parametrize(
    "language,day,tariff",
    [
        ("en", "Monday", "Off-peak"),
        ("es", "Lunes", "Valle"),
        ("fr", "Lundi", "Heures creuses"),
    ],
)
async def test_edit_and_remove_choices_use_translated_labels(
    hass, language, day, tariff
):
    entry = MockConfigEntry(domain=DOMAIN, data={"ip_address": "192.0.2.10"})
    entry.add_to_hass(hass)
    blocks = [
        {"days": ["mon"], "start": "00:00:00", "end": "08:00:00", "period": "off_peak"}
    ]
    choices = await async_block_choices(hass, blocks, language)
    assert choices == [{"value": "0", "label": f"{day}: 00:00 → 08:00 — {tariff}"}]


@pytest.mark.parametrize(
    "step",
    ["settings", "add_block", "edit_block", "edit_details", "remove_block", "save"],
)
@pytest.mark.parametrize("action", ["back", "cancel"])
async def test_form_navigation_never_applies_current_screen(hass, step, action):
    """Back needs no block selection; even a checked summary cannot apply it."""
    configured = options()
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=deepcopy(configured)
    )
    entry.add_to_hass(hass)
    if step == "edit_details":
        flow, result = await start_edit(hass, entry.entry_id)
    else:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        flow = result["flow_id"]
        result = await hass.config_entries.options.async_configure(
            flow, {"next_step_id": step}
        )
    assert result["step_id"] == step
    payload = {"navigation": action}
    if step == "save":
        payload["confirm"] = True
    if step == "settings":
        payload.update(enabled=False, allowed=[])
    result = await hass.config_entries.options.async_configure(flow, payload)
    assert entry.options == configured
    if action == "cancel":
        assert result["type"] == "abort"
        assert result["reason"] == "changes_cancelled"
    else:
        assert result["type"] == "menu"
        result = await hass.config_entries.options.async_configure(
            flow, {"next_step_id": "save"}
        )
        result = await hass.config_entries.options.async_configure(
            flow, {"confirm": True}
        )
        assert result["type"] == "create_entry"
        assert entry.options == configured


@pytest.mark.parametrize("step", ["edit_block", "remove_block"])
async def test_continue_requires_a_block_but_back_does_not(hass, step):
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=options()
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    flow = result["flow_id"]
    await hass.config_entries.options.async_configure(flow, {"next_step_id": step})
    result = await hass.config_entries.options.async_configure(
        flow, {"navigation": "continue"}
    )
    assert result["errors"] == {"block": "choose_block"}
    result = await hass.config_entries.options.async_configure(
        flow, {"navigation": "back"}
    )
    assert result["type"] == "menu"
    hass.config_entries.options.async_abort(flow)


@pytest.mark.parametrize("cancel_method", ["menu", "close"])
async def test_cancel_discards_previously_accepted_draft_and_reopens_saved_options(
    hass, cancel_method
):
    configured = options()
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=deepcopy(configured)
    )
    entry.add_to_hass(hass)
    flow, _result = await start_edit(hass, entry.entry_id)
    changed = {
        "days": ["tue"],
        "start": "01:00:00",
        "end": "06:00:00",
        "period": "peak",
    }
    result = await hass.config_entries.options.async_configure(flow, changed)
    assert result["type"] == "menu"
    assert entry.options == configured
    if cancel_method == "menu":
        result = await hass.config_entries.options.async_configure(
            flow, {"next_step_id": "cancel"}
        )
        assert result["type"] == "abort"
    else:
        hass.config_entries.options.async_abort(flow)
    flow, result = await start_edit(hass, entry.entry_id)
    assert {
        key.schema: key.default()
        for key in result["data_schema"].schema
        if key.schema != "navigation"
    } == configured["scheduling"]["blocks"][0]
    assert entry.options == configured
    hass.config_entries.options.async_abort(flow)


async def test_back_after_invalid_edit_preserves_accepted_draft(hass):
    configured = options()
    entry = MockConfigEntry(
        domain=DOMAIN, data={"ip_address": "192.0.2.10"}, options=deepcopy(configured)
    )
    entry.add_to_hass(hass)
    flow, _result = await start_edit(hass, entry.entry_id)
    changed = {
        "days": ["mon"],
        "start": "01:00:00",
        "end": "06:00:00",
        "period": "peak",
    }
    await hass.config_entries.options.async_configure(flow, changed)
    await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "edit_block"}
    )
    await hass.config_entries.options.async_configure(flow, {"block": "0"})
    result = await hass.config_entries.options.async_configure(
        flow, {**changed, "end": "01:00:00"}
    )
    assert result["errors"] == {"base": "invalid_schedule"}
    result = await hass.config_entries.options.async_configure(
        flow, {"navigation": "back"}
    )
    assert result["type"] == "menu"
    await hass.config_entries.options.async_configure(flow, {"next_step_id": "save"})
    result = await hass.config_entries.options.async_configure(flow, {"confirm": True})
    assert result["type"] == "create_entry"
    assert entry.options["scheduling"]["blocks"] == [changed]


@pytest.mark.parametrize("action", ["back", "cancel"])
async def test_invalid_summary_can_be_abandoned(hass, action):
    entry = MockConfigEntry(domain=DOMAIN, data={"ip_address": "192.0.2.10"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    flow = result["flow_id"]
    await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "settings"}
    )
    await hass.config_entries.options.async_configure(
        flow, {"enabled": True, "allowed": ["off_peak"]}
    )
    result = await hass.config_entries.options.async_configure(
        flow, {"next_step_id": "save"}
    )
    assert result["step_id"] == "save_error"
    result = await hass.config_entries.options.async_configure(
        flow, {"navigation": action}
    )
    assert result["type"] == ("menu" if action == "back" else "abort")
    assert not entry.options
    if action == "back":
        hass.config_entries.options.async_abort(flow)


async def test_cancelling_options_does_not_reload_or_command_a_running_charger(hass):
    async for entry, _data, command in setup_charger(hass, options()):
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        manager = coordinator.scheduler
        configured = deepcopy(entry.options)
        command.reset_mock()
        flow, _result = await start_edit(hass, entry.entry_id)
        await hass.config_entries.options.async_configure(
            flow,
            {"days": ["mon"], "start": "01:00:00", "end": "06:00:00", "period": "peak"},
        )
        result = await hass.config_entries.options.async_configure(
            flow, {"next_step_id": "cancel"}
        )
        await hass.async_block_till_done()
        assert result["type"] == "abort"
        assert entry.options == configured
        assert entry.runtime_data is coordinator
        assert coordinator.scheduler is manager
        assert not manager._stopped
        command.assert_not_awaited()
