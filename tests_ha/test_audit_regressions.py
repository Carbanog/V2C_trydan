"""Regression tests from the beta audit; all charger IO is simulated."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script, async_validate_actions_config
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.v2c_trydan.api import V2CTrydanApi
from custom_components.v2c_trydan.diagnostics import async_get_config_entry_diagnostics
from tests_ha.test_scheduling_integration import DOMAIN, setup_charger


def entity_id(hass, entry, suffix):
    from homeassistant.helpers import entity_registry as er

    platform = "binary_sensor" if suffix == "connected" else "sensor"
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.unique_id}_{suffix}"
    )


@pytest.mark.parametrize("final_state", [0, 2])
async def test_fault_does_not_report_false_unplug(hass, final_state):
    async for entry, data, _command in setup_charger(hass, {}):
        cable = entity_id(hass, entry, "connected")
        assert hass.states.get(cable).state == "on"
        for state in (3, 4, 5, 6):
            data["ChargeState"] = state
            await entry.runtime_data.async_refresh()
            await hass.async_block_till_done()
            assert hass.states.get(cable).state == "on"
        # A restart during a fault must use the persisted physical state too.
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(cable).state == "on"
        data["ChargeState"] = final_state
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get(cable).state == ("off" if final_state == 0 else "on")


async def test_reconfigure_ip_reloads_once_and_preserves_identity(hass):
    async for entry, _data, _command in setup_charger(hass, {}):
        previous_options = dict(entry.options)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
        )
        with (
            patch.object(
                V2CTrydanApi,
                "async_get_realtime_data",
                return_value={"ID": entry.unique_id},
            ),
            patch.object(
                hass.config_entries, "async_reload", new_callable=AsyncMock
            ) as reload,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"ip_address": "192.0.2.11"}
            )
            await hass.async_block_till_done()
        assert result["type"] == "abort"
        assert result["reason"] == "reconfigure_successful"
        assert entry.data["ip_address"] == "192.0.2.11"
        assert entry.unique_id == "example-charger"
        assert entry.options == previous_options
        reload.assert_awaited_once_with(entry.entry_id)


@pytest.mark.parametrize(
    "service,field,value",
    [
        ("set_min_intensity", "min_intensity", 16),
        ("set_max_intensity", "max_intensity", 6),
        ("set_intensity", "intensity", 16),
    ],
)
async def test_service_rejects_conflicting_intensity_without_write(
    hass, service, field, value
):
    async for entry, data, command in setup_charger(hass, {}):
        data.update(MinIntensity=7, MaxIntensity=15)
        await entry.runtime_data.async_refresh()
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, service, {field: value}, blocking=True
            )
        command.assert_not_awaited()


async def test_diagnostics_omit_unknown_firmware_and_config_fields(hass):
    async for entry, data, _command in setup_charger(hass, {}):
        data.update(
            SSID="example-network", IP="192.0.2.10", FutureIdentifier="private-example"
        )
        await entry.runtime_data.async_refresh()
        with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "future_secret": "private-example"}
            )
            diagnostics = await async_get_config_entry_diagnostics(hass, entry)
            await hass.async_block_till_done()
        assert diagnostics["data"]["ChargePower"] == 1000
        assert diagnostics["data"]["SSID"] == "**REDACTED**"
        assert diagnostics["config_entry"]["ip_address"] == "**REDACTED**"
        assert "FutureIdentifier" not in diagnostics["data"]
        assert "future_secret" not in diagnostics["config_entry"]


async def test_blueprint_waits_for_first_charge_after_two_days(hass):
    inputs = {
        "cable_connected": "binary_sensor.example_cable",
        "charging": "binary_sensor.example_charging",
        "session_energy": "sensor.example_energy",
        "session_active_time": "sensor.example_time",
        "battery_capacity": 0,
        "charging_efficiency": 90,
        "electricity_price": 0,
        "vehicle_efficiency": 0,
        "start_actions": [{"event": "example_charge_started"}],
        "finish_actions": [],
    }

    class BlueprintLoader(yaml.SafeLoader):
        """Resolve only this test's explicit blueprint inputs."""

    BlueprintLoader.add_constructor(
        "!input", lambda loader, node: inputs[loader.construct_scalar(node)]
    )
    path = Path(__file__).parents[1] / "blueprints/automation/session_summary.yaml"
    config = yaml.load(path.read_text(encoding="utf-8"), Loader=BlueprintLoader)
    calls = []
    hass.bus.async_listen("example_charge_started", lambda event: calls.append(event))
    hass.states.async_set(inputs["cable_connected"], "on")
    hass.states.async_set(inputs["charging"], "off")
    # Exercise the actual first-charge branch. The outer choose creates tracked
    # child tasks, which block HA's test drain while this branch intentionally waits.
    start_sequence = config["actions"][0]["choose"][0]["sequence"]
    actions = await async_validate_actions_config(hass, cv.SCRIPT_SCHEMA(start_sequence))
    runner = Script(hass, actions, "Example session notifications", "automation")
    # An intentionally waiting script is background work. A tracked automation
    # trigger would make block_till_done wait for the very charge we must simulate.
    task = hass.async_create_background_task(
        runner.async_run({**config["variables"], "trigger": {"id": "connected"}}),
        "example session notification test",
        eager_start=True,
    )
    try:
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=49))
        await hass.async_block_till_done()
        assert not calls
        assert runner.is_running
        hass.states.async_set(inputs["charging"], "on")
        await task
        await hass.async_block_till_done()
        assert len(calls) == 1
        hass.states.async_set(inputs["charging"], "off")
        hass.states.async_set(inputs["charging"], "on")
        await hass.async_block_till_done()
        assert len(calls) == 1
    finally:
        await runner.async_stop()
        await task
