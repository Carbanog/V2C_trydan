"""Repository metadata tests."""

from __future__ import annotations

import ast
import json
import re
import struct
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "v2c_trydan"
READMES = ("README.md", "README.es.md", "README.fr.md")


def test_local_brand_icon_is_valid_png() -> None:
    """Keep HACS branding self-contained and protect against corrupt downloads."""
    content = (INTEGRATION / "brand" / "icon.png").read_bytes()
    assert content[:8] == b"\x89PNG\r\n\x1a\n"
    assert content[12:16] == b"IHDR"
    assert struct.unpack_from(">II", content, 16) == (256, 256)
    assert content[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82"


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


def test_funding_uses_the_project_support_url() -> None:
    """Expose optional support through GitHub without third-party widgets."""
    funding = yaml.safe_load((ROOT / ".github" / "FUNDING.yml").read_text())
    assert funding == {"custom": ["https://buymeacoffee.com/Carbanog"]}


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


@pytest.mark.parametrize(
    "language",
    sorted(path.stem for path in (INTEGRATION / "translations").glob("*.json")),
)
def test_translation_files_have_the_same_keys(language: str) -> None:
    """Every supplied language must cover the complete integration interface."""
    english = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    translated = json.loads(
        (INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8")
    )
    assert _key_shape(english) == _key_shape(translated)

    def assert_translated_text(value: object) -> None:
        if isinstance(value, dict):
            for child in value.values():
                assert_translated_text(child)
        else:
            assert isinstance(value, str) and value.strip()

    assert_translated_text(translated)


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


def test_measured_sensors_use_optional_firmware_fields() -> None:
    """L1 telemetry must use actual measurements without requiring new firmware."""
    for entity_key, api_key, unit in (
        ("measured_current_l1", "IntensityMeasure_L1", "UnitOfElectricCurrent.AMPERE"),
        ("measured_voltage_l1", "VoltageMeasure_L1", "UnitOfElectricPotential.VOLT"),
    ):
        description = _sensor_description_keywords(entity_key)
        assert ast.literal_eval(description["required_key"]) == api_key
        assert ast.unparse(description["native_unit_of_measurement"]) == unit
        assert ast.unparse(description["state_class"]) == "SensorStateClass.MEASUREMENT"
        assert ast.literal_eval(description["suggested_display_precision"]) == 2


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
        "measured_current_l1",
        "measured_voltage_l1",
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
        if line.startswith("## ") and line != "## Unreleased"
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
        for readme_name in READMES:
            readme = (ROOT / readme_name).read_text(encoding="utf-8")
            assert f"blueprints/automation/{path.name}" in readme
            assert f"v{version}%2Fblueprints%2Fautomation%2F{path.name}" in readme


def test_hacs_install_link_is_available_in_all_readmes() -> None:
    """Keep the one-click custom-repository installation path discoverable."""
    install_url = (
        "https://my.home-assistant.io/redirect/hacs_repository/"
        "?owner=Carbanog&repository=V2C_trydan&category=integration"
    )
    for readme_name in READMES:
        readme = (ROOT / readme_name).read_text(encoding="utf-8")
        assert "https://my.home-assistant.io/badges/hacs_repository.svg" in readme
        assert install_url in readme


def test_dashboard_screenshots_are_local_and_documented() -> None:
    """Keep README screenshots self-contained instead of hot-linking attachments."""
    for image_name in ("dashboard-native.png", "dashboard-mushroom.png"):
        relative_path = f"docs/images/{image_name}"
        image_path = ROOT / relative_path
        assert image_path.is_file()
        assert image_path.stat().st_size > 0
        for readme_name in READMES:
            readme = (ROOT / readme_name).read_text(encoding="utf-8")
            assert relative_path in readme


def test_supported_languages_have_readmes_and_navigation() -> None:
    """Do not publish a language selector pointing at a missing translation."""
    for language_file in (INTEGRATION / "translations").glob("*.json"):
        language = language_file.stem
        readme_name = "README.md" if language == "en" else f"README.{language}.md"
        assert (ROOT / readme_name).is_file()
        for other in READMES:
            assert f"]({readme_name})" in (ROOT / other).read_text(encoding="utf-8")


def test_relative_readme_links_resolve_inside_repository() -> None:
    """Protect install guides, YAML examples, images, credits and navigation."""
    for readme_name in READMES:
        readme = (ROOT / readme_name).read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^\s)]+)\)", readme):
            if ":" in link or link.startswith("#"):
                continue
            target = (ROOT / link.split("#", 1)[0]).resolve()
            assert target.is_relative_to(ROOT.resolve())
            assert target.exists(), (readme_name, link)


def test_original_license_credit_is_preserved() -> None:
    """Documentation cleanup must not remove the inherited MIT attribution."""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Copyright (c) 2023 Rafael S." in license_text
    assert "Copyright (c) 2026 Carbanog" in license_text
