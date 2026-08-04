# V2C Trydan for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://www.hacs.xyz/)
[![GitHub release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[![English](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![Español](https://img.shields.io/badge/lang-es-yellow.svg)](README.es.md)

A local Home Assistant integration for monitoring and controlling **V2C Trydan**
chargers. It is designed for PLC and weak Wi-Fi links that benefit from paced,
serialized requests and graceful handling of temporary failures.

> [!IMPORTANT]
> This is an independent community project and is not affiliated with V2C. It
> derives from [Rain1971's original work](https://github.com/Rain1971/V2C_trydant)
> and is provided without warranty. Test beta releases on a non-production Home
> Assistant instance first.

## Highlights

- Fully local HTTP communication with no third-party Python dependency.
- One coordinated poll every 15 seconds shared by all entities.
- Retries and serialized requests suited to constrained network links.
- Pause, lock, and current controls.
- **Whole-session energy and active time** across counter resets caused by OCPP
  or app pauses.
- Session persistence across Home Assistant restarts.
- Descriptive charge states and immediate meter-problem detection.
- UI-based IP reconfiguration without recreating entities.
- Privacy-safe diagnostics that redact IP, SSID, and hardware identifiers.
- Optional automation blueprints and dashboard examples.

## Installation

1. Add `https://github.com/Carbanog/V2C_trydan` to HACS as a custom
   **Integration** repository.
2. Install V2C Trydan and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **V2C Trydan** and enter the charger's local IP address.

Reserve the address in your router's DHCP server. If it changes, choose
**Reconfigure** from the integration menu instead of deleting the integration.

## A focused default experience

New installations enable only everyday entities. Internal settings, solar and
home-battery data, and detailed diagnostics remain available on the device page
but start disabled.

Disabling an entity in Home Assistant **does not modify the charger**. Dynamic
charging, for example, remains active when configured through the V2C app.

### Enabled by default

| Entity | Type | Purpose |
| --- | --- | --- |
| Charge Power | Sensor | Power delivered to the vehicle. |
| Charge Energy | Sensor | Partial counter reported by firmware. |
| Session Energy | Sensor | Local total across every segment until the next connection. |
| Session Active Charging Time | Sensor | Local active-time total across every segment. |
| Charge State | Sensor | Detailed charger state. |
| House Power | Sensor | Consumption seen by dynamic regulation. |
| Cable Connected | Binary sensor | Reliable session automation trigger. |
| Charging | Binary sensor | Active charging flow. |
| Meter Problem | Binary sensor | Warns when the meter reports any error code. |
| Pause Charge | Switch | Manually pauses or resumes charging. |
| Lock Charger | Switch | Controls charger locking. |
| Charge Intensity | Number | Sets manual current from 6 to 32 A. |

### Advanced and diagnostic entities

Photovoltaic and home-battery power, voltage, contracted power, minimum and
maximum current, dynamic charging, dynamic mode, timer, dynamic pause, duplicate
raw states (including the firmware's per-segment `Charge Time`), meter codes,
firmware, IP, SSID, Wi-Fi signal, and hardware ID start disabled. Enable only the
entities relevant to the installation from
**Settings → Devices & services → Entities**.

Changing a default never overrides an entity choice already stored by an
upgrading user.

## Whole-session statistics

`Charge Energy` mirrors the charger's `ChargeEnergy` property. External
controllers such as OCPP may split one physical connection into several charging
segments and reset that value after a pause.

`Session Energy` and `Session Active Charging Time` add the positive increments
from every segment while the cable remains connected. They retain the finished
totals after disconnection for delayed summary automations, reset at the next
vehicle connection, and periodically persist independently of Recorder.

The disabled-by-default `Reset Session Statistics` button handles exceptional
manual correction without recounting the current raw baselines.

> [!NOTE]
> Energy from complete segments that occur while Home Assistant is offline and
> are later erased by the charger cannot be recovered.

## Reusable automations

Blueprints are never installed or enabled automatically. Import them through
**Settings → Automations & scenes → Blueprints → Import blueprint**:

- [Session summary and notifications](blueprints/automation/session_summary.yaml)
  exposes variables for kWh, active time, estimated percentage added, cost, and
  range.
- [High charging power alert](blueprints/automation/high_power_alert.yaml) has a
  configurable threshold, duration, and action sequence.

Battery capacity, efficiency, price, and range describe the vehicle or tariff,
not the charger. They therefore belong to the optional blueprint rather than the
core integration. Calculated percentages are **estimated energy added**, not a
vehicle-reported state of charge.

## Dashboard examples

- [Native dashboard](dashboards/native.en.yaml) uses built-in Home Assistant
  cards only.
- [Mushroom dashboard](dashboards/mushroom.en.yaml) requires Mushroom and Mini
  Graph Card.

Paste a selected example into a manual dashboard card and adjust entity IDs if
Home Assistant generated different names. The integration never changes a
dashboard automatically.

## Compatibility actions

| Action | Description |
| --- | --- |
| `v2c_trydan.set_intensity` | Sets manual charging current. |
| `v2c_trydan.set_min_intensity` | Sets the lower dynamic-current limit. |
| `v2c_trydan.set_max_intensity` | Sets the upper dynamic-current limit. |
| `v2c_trydan.set_dynamic_power_mode` | Changes dynamic strategy from 0 to 5. |

New automations should normally target `number`, `select`, and `switch` entities
directly. These actions remain for backwards compatibility and support explicit
charger selection in multi-charger installations.

> [!WARNING]
> The V2C app exposes settings that the local API does not, including scheduled
> contracted-power limits. Do not change dynamic charging, timer, or advanced
> modes from Home Assistant when they protect the installation or when an energy
> provider controls charging through OCPP.

## Technical behavior

| Parameter | Value |
| --- | --- |
| Main poll | 15 seconds |
| Read timeout | 20 seconds |
| Retries | 3, with a 2-second delay |
| Concurrency | One in-flight request per charger |
| Session persistence | On connection changes and during long charges |

Light controls were removed after physical testing with firmware 2.4.6 because
their local API state did not reliably match the charger or V2C app. Reliable
state is required before a control can return in a future release.

## Diagnostics

- Verify `http://CHARGER_IP/RealTimeData` from the same network.
- Temporary failures make entities unavailable and are retried automatically.
- Download diagnostics from the integration menu when reporting a problem;
  sensitive network and identity values are redacted.
- See [`docs/architecture.md`](docs/architecture.md) for module boundaries,
  invariants, compatibility policy, and contribution guidance.

## Credits

- [Rain1971](https://github.com/Rain1971/V2C_trydant), author of the original
  integration this project started from.
- The Home Assistant community and AI tools used during development and review.
