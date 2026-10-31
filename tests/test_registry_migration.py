"""Execute the real migration in isolation with explicit registry test doubles.

The lightweight suite does not install HA. Only the production function is
compiled from its AST; imports and setup are not run. These tests cover registry
selection and updates, not Home Assistant's own persistence implementation.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

DOMAIN = "v2c_trydan"
ENTRY_ID = "example-entry"
LEGACY_ID = "192.0.2.10"
HARDWARE_ID = "example-charger"


def _device(identifier: str, entry_id: str = ENTRY_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"{entry_id}-{identifier}",
        identifiers={(DOMAIN, identifier)},
        config_entries={entry_id},
        name_by_user="My charger",
        area_id="garage",
    )


@pytest.fixture(params=[True, False], ids=["modern-ha", "older-ha"])
def migration(request: pytest.FixtureRequest):
    """Run the production migration with either supported registry interface."""
    devices: list[SimpleNamespace] = []
    registry = SimpleNamespace(async_update_device=Mock())

    def own_devices(registry_arg, config_entry_id):
        assert registry_arg is registry
        return [d for d in devices if config_entry_id in d.config_entries]

    if request.param:

        def lookup(identifier, config_entry_id):
            return next(
                (
                    d
                    for d in own_devices(registry, config_entry_id)
                    if identifier in d.identifiers
                ),
                None,
            )

        registry.async_get_device_by_identifier = Mock(side_effect=lookup)

    entities = SimpleNamespace(
        async_get_entity_id=Mock(return_value=None), async_update_entity=Mock()
    )
    source = (
        Path(__file__).parents[1] / "custom_components/v2c_trydan/__init__.py"
    ).read_text(encoding="utf-8")
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_migrate_legacy_registry_entries"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {
        "DOMAIN": DOMAIN,
        "CONF_IP_ADDRESS": "ip_address",
        "_LEGACY_ENTITY_SUFFIXES": {"sensor": ("charge_power",)},
        "dr": SimpleNamespace(
            async_get=lambda hass: registry,
            async_entries_for_config_entry=own_devices,
        ),
        "er": SimpleNamespace(async_get=lambda hass: entities),
    }
    exec(compile(module, "<production registry migration>", "exec"), namespace)
    entry = SimpleNamespace(entry_id=ENTRY_ID, data={"ip_address": LEGACY_ID})
    return SimpleNamespace(
        run=lambda device_id=HARDWARE_ID: namespace["_migrate_legacy_registry_entries"](
            None, entry, device_id
        ),
        devices=devices,
        registry=registry,
        entities=entities,
    )


def test_migrates_own_device_without_changing_registry_id_or_customizations(migration):
    device = _device(LEGACY_ID)
    migration.devices.append(device)
    original = vars(device).copy()
    migration.entities.async_get_entity_id.side_effect = ["sensor.my_power", None]
    migration.run()
    migration.registry.async_update_device.assert_called_once_with(
        device.id, new_identifiers={(DOMAIN, HARDWARE_ID)}
    )
    migration.entities.async_update_entity.assert_called_once_with(
        "sensor.my_power", new_unique_id=f"{HARDWARE_ID}_charge_power"
    )
    assert vars(device) == original


def test_foreign_legacy_device_is_not_migrated(migration):
    migration.devices.append(_device(LEGACY_ID, "other-entry"))
    migration.run()
    migration.registry.async_update_device.assert_not_called()


def test_foreign_hardware_identifier_does_not_block_own_migration(migration):
    own = _device(LEGACY_ID)
    migration.devices.extend([_device(HARDWARE_ID, "other-entry"), own])
    migration.run()
    migration.registry.async_update_device.assert_called_once_with(
        own.id, new_identifiers={(DOMAIN, HARDWARE_ID)}
    )


def test_existing_own_hardware_device_is_not_overwritten(migration):
    migration.devices.extend([_device(LEGACY_ID), _device(HARDWARE_ID)])
    migration.run()
    migration.registry.async_update_device.assert_not_called()


def test_already_migrated_entity_is_not_overwritten(migration):
    migration.entities.async_get_entity_id.side_effect = [
        "sensor.legacy_power",
        "sensor.current_power",
    ]
    migration.run()
    migration.entities.async_update_entity.assert_not_called()


def test_identical_ip_and_hardware_id_needs_no_registry_access(migration):
    migration.run(LEGACY_ID)
    migration.registry.async_update_device.assert_not_called()
    migration.entities.async_get_entity_id.assert_not_called()
