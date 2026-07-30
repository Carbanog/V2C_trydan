"""Repository metadata tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "v2c_trydan"


def test_json_files_are_valid() -> None:
    """All integration JSON metadata must be parseable."""
    for path in INTEGRATION.rglob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)


def test_yaml_files_are_valid() -> None:
    """Actions and GitHub workflows must be parseable YAML."""
    paths = [INTEGRATION / "services.yaml", *ROOT.glob(".github/workflows/*")]
    for path in paths:
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict)


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
