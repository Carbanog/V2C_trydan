"""Exercise actual HA setup/options/entity/lifecycle code, with a fake charger."""

from copy import deepcopy
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

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
        patch(
            f"custom_components.{DOMAIN}.api.V2CTrydanApi.async_get_realtime_data",
            side_effect=read,
        ),
        patch(
            f"custom_components.{DOMAIN}.api.V2CTrydanApi.async_write",
            side_effect=write,
        ) as command,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry, data, command
        if getattr(entry, "runtime_data", None) is not None:
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
        data["ChargeState"] = 0
        await entry.runtime_data.async_request_refresh()
        await hass.async_block_till_done()
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
    assert result["type"] == "create_entry"
    assert entry.options["unrelated"] == "keep"
    assert entry.options["scheduling"]["enabled"] is False
    assert len(entry.options["scheduling"]["blocks"]) == 1
