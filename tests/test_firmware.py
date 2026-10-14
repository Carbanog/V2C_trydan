"""Compatibility checks against anonymized recorded firmware responses."""

from pathlib import Path

import pytest

from custom_components.v2c_trydan.api import parse_realtime_data
from custom_components.v2c_trydan.session import SessionTracker

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "name,version",
    (
        ("realtime_2_4_6.json", "2.4.6"),
        ("realtime_2_5_1_idle.json", "2.5.1"),
        ("realtime_2_5_1_charging.json", "2.5.1"),
    ),
)
def test_recorded_firmware_response_remains_supported(name: str, version: str) -> None:
    """Additional keys and old duplicate keys must not break core readings."""
    data = parse_realtime_data((FIXTURES / name).read_text(encoding="utf-8"))
    assert data["FirmwareVersion"] == version
    assert data["ID"] == "example-charger"


def test_measured_values_are_distinct_from_configured_values() -> None:
    """Do not substitute the current setpoint or reference installation voltage."""
    data = parse_realtime_data(
        (FIXTURES / "realtime_2_5_1_charging.json").read_text(encoding="utf-8")
    )
    assert data["IntensityMeasure_L1"] == 13.48
    assert data["Intensity"] == 14
    assert data["VoltageMeasure_L1"] == 220.12
    assert data["VoltageInstallation"] == 222


def test_firmware_251_snapshots_feed_session_tracker() -> None:
    """A physical charging sample still follows the existing session contract."""
    tracker = SessionTracker()
    for name in ("realtime_2_5_1_idle.json", "realtime_2_5_1_charging.json"):
        data = parse_realtime_data((FIXTURES / name).read_text(encoding="utf-8"))
        tracker.update(data["ChargeState"], data["ChargeEnergy"], data["ChargeTime"])
    assert tracker.energy == pytest.approx(0.37)
    assert tracker.active_time == 454
