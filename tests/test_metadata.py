"""Repository metadata tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "v2c_trydan"


class _BlueprintLoader(yaml.SafeLoader):
    """Parse Home Assistant input tags without interpreting their values."""


def _construct_blueprint_input(loader: _BlueprintLoader, node: yaml.ScalarNode) -> str:
    """Keep a blueprint input reference as a plain scalar for structure tests."""
    return loader.construct_scalar(node)


_BlueprintLoader.add_constructor("!input", _construct_blueprint_input)


def test_json_files_are_valid() -> None:
    """All integration JSON metadata must be parseable."""
    for path in INTEGRATION.rglob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)


def test_yaml_files_are_valid() -> None:
    """Integration metadata, examples, and workflows must be parseable YAML."""
    paths = [
        INTEGRATION / "services.yaml",
        *ROOT.glob(".github/workflows/*"),
        *ROOT.glob("blueprints/**/*.yaml"),
        *ROOT.glob("dashboards/*.yaml"),
    ]
    for path in paths:
        loader = _BlueprintLoader if "blueprints" in path.parts else yaml.SafeLoader
        assert isinstance(
            yaml.load(path.read_text(encoding="utf-8"), Loader=loader), dict
        )


def _key_shape(value: object) -> object:
    """Return a nested representation containing keys but not translations."""
    if isinstance(value, dict):
        return {key: _key_shape(child) for key, child in value.items()}
    return None


def test_translation_files_have_the_same_keys() -> None:
    """Spanish and English translation structures must not drift."""
    english = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    spanish = json.loads(
        (INTEGRATION / "translations" / "es.json").read_text(encoding="utf-8")
    )
    assert _key_shape(english) == _key_shape(spanish)


def test_service_translation_fields_match_service_metadata() -> None:
    """Service field translations must use HA-valid keys and match services.yaml."""
    services = yaml.safe_load(
        (INTEGRATION / "services.yaml").read_text(encoding="utf-8")
    )
    translations = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )

    for service_name, service in services.items():
        service_fields = set(service.get("fields", {}))
        translated_fields = set(
            translations["services"][service_name].get("fields", {})
        )
        assert translated_fields == service_fields
        assert all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", field)
            for field in translated_fields
        )


def _sensor_description_keywords(entity_key: str) -> dict[str | None, ast.expr]:
    """Return AST keywords for one sensor entity description."""
    tree = ast.parse((INTEGRATION / "sensor.py").read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "V2CSensorEntityDescription"
        ):
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        key = keywords.get("key")
        if isinstance(key, ast.Constant) and key.value == entity_key:
            return keywords

    raise AssertionError(f"{entity_key} sensor description not found")


def test_statistics_state_classes_do_not_regress() -> None:
    """Protect long-term statistics created by releases before the refactor."""
    measurement_keys = (
        "signal_status",
        "dynamic",
        "dynamic_power_mode",
        "locked",
        "paused",
        "pause_dynamic",
        "slave_error",
        "timer",
        "ready_state",
    )
    for entity_key in measurement_keys:
        description = _sensor_description_keywords(entity_key)
        assert ast.unparse(description["state_class"]) == "SensorStateClass.MEASUREMENT"

    charge_time = _sensor_description_keywords("charge_time")
    assert (
        ast.unparse(charge_time["state_class"]) == "SensorStateClass.TOTAL_INCREASING"
    )

    session_time = _sensor_description_keywords("session_active_time")
    assert (
        ast.unparse(session_time["state_class"]) == "SensorStateClass.TOTAL_INCREASING"
    )
    assert (
        ast.unparse(session_time["native_unit_of_measurement"]) == "UnitOfTime.SECONDS"
    )
    assert (
        ast.unparse(session_time["suggested_unit_of_measurement"]) == "UnitOfTime.HOURS"
    )
    precision = session_time["suggested_display_precision"]
    assert isinstance(precision, ast.Constant)
    assert precision.value == 2


def test_session_energy_uses_two_display_decimals() -> None:
    """Keep the UI readable without rounding the coordinator value."""
    description = _sensor_description_keywords("session_energy")
    precision = description["suggested_display_precision"]
    assert isinstance(precision, ast.Constant)
    assert precision.value == 2


def test_default_sensor_surface_remains_focused() -> None:
    """New installs should not enable optional or duplicate readback sensors."""
    tree = ast.parse((INTEGRATION / "sensor.py").read_text(encoding="utf-8"))
    disabled: set[str] = set()
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "V2CSensorEntityDescription"
        ):
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        key = keywords.get("key")
        enabled_default = keywords.get("entity_registry_enabled_default")
        if (
            isinstance(key, ast.Constant)
            and isinstance(enabled_default, ast.Constant)
            and enabled_default.value is False
        ):
            disabled.add(str(key.value))

    assert disabled == {
        "battery_power",
        "charge_time",
        "contracted_power",
        "device_id",
        "dynamic",
        "dynamic_power_mode",
        "firmware_version",
        "fv_power",
        "intensity",
        "ip_address",
        "locked",
        "max_intensity",
        "meter_error",
        "min_intensity",
        "pause_dynamic",
        "paused",
        "ready_state",
        "signal_status",
        "slave_error",
        "ssid",
        "timer",
        "voltage_installation",
    }


def test_manifest_version_matches_latest_changelog() -> None:
    """Release metadata and the top changelog section must remain aligned."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest_heading = next(
        line.removeprefix("## ")
        for line in changelog.splitlines()
        if line.startswith("## ")
    )
    assert manifest["version"] == latest_heading


def test_retired_light_platform_is_not_loaded() -> None:
    """Unreliable beta light controls must not return accidentally."""
    init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    platforms_assignment = next(
        node
        for node in ast.parse(init_source).body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PLATFORMS"
    )
    assert "Platform.LIGHT" not in ast.unparse(platforms_assignment)
    assert not (INTEGRATION / "light.py").exists()
    assert "_remove_retired_beta_lights" in init_source


def test_blueprint_release_links_are_current_and_documented() -> None:
    """Import links must target the released files and remain discoverable."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    blueprint_paths = tuple(ROOT.glob("blueprints/automation/*.yaml"))
    for path in blueprint_paths:
        blueprint = yaml.load(path.read_text(encoding="utf-8"), Loader=_BlueprintLoader)
        assert (
            f"/blob/v{version}/blueprints/automation/{path.name}"
            in blueprint["blueprint"]["source_url"]
        )
        for readme_name in ("README.md", "README.es.md"):
            readme = (ROOT / readme_name).read_text(encoding="utf-8")
            assert f"blueprints/automation/{path.name}" in readme
            assert f"v{version}%2Fblueprints%2Fautomation%2F{path.name}" in readme
