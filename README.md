<img src="custom_components/v2c_trydan/brand/icon.png" alt="V2C" width="64" align="right">

# V2C Trydan for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Stable release](https://img.shields.io/github/v/release/Carbanog/V2C_trydan.svg)](https://github.com/Carbanog/V2C_trydan/releases/)
[![Validation](https://github.com/Carbanog/V2C_trydan/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/Carbanog/V2C_trydan/actions/workflows/validate.yml)
[![MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) · [Español](README.es.md) · [Français](README.fr.md)

[Install](#installation) · [Entities](#entities-and-configuration) · [Sessions](#session-accounting) · [Scheduling](#optional-charging-schedules) · [Blueprints](#blueprints-and-automations) · [Dashboards](#dashboards)

Local charger control, complete charging-session tracking, and optional tools
for managing charging from Home Assistant.

V2C Trydan combines everyday controls, persistent sessions across pauses and
restarts, diagnostics and reusable automations, including optional
weekly tariff scheduling without relying on an energy provider.

## At a glance

| Native dashboard | Mushroom dashboard |
| :---: | :---: |
| [![Native dashboard](docs/images/dashboard-native.png)](docs/images/dashboard-native.png) | [![Mushroom dashboard](docs/images/dashboard-mushroom.png)](docs/images/dashboard-mushroom.png) |

Real dashboard examples. Screenshots are in Spanish; entities follow your HA language.

## Releases and scope

| Channel | Version | Purpose |
| --- | --- | --- |
| Stable | [1.4.0](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.4.0) | Monitoring, controls, sessions and optional scheduling. |
| Previous stable | [1.3.3](https://github.com/Carbanog/V2C_trydan/releases/tag/v1.3.3) | Rollback version without scheduling. |

Scheduling is disabled by default. Automated checks do not certify physical
charging behavior in every installation; supervise the first schedule changes.
See the [changelog](CHANGELOG.md).
Install through HACS as a **custom repository**; this project is not presented
as included in the default HACS catalog.

## Features

| Capability | What it gives you |
| --- | --- |
| **Local control** | Pause, lock and current controls over local HTTP. No V2C Cloud account or Octopus/OCPP required. |
| **Whole-session tracking** | Energy and active time across pauses, counter resets and HA restarts. |
| **Communication and diagnostics** | Shared serialized requests, bounded retries, redacted diagnostics and IP reconfiguration without recreating the integration. |
| **Optional extensions** | Weekly tariff scheduling, importable blueprints, native/Mushroom dashboards and English, Spanish and French UI. |

Fault tolerance does not eliminate network problems or guarantee connectivity.

## Requirements and compatibility

Home Assistant **2026.3.1 or newer** is required. The declared minimum and the
2026.10.4 baseline run full HA tests; 2026.11 has import-only smoke coverage.

HA must reach the charger's local HTTP API. Reserve its address in your router
and check `http://CHARGER_IP/RealTimeData` on the same network.
Do not expose that API to the Internet.

Tests include anonymized real responses from firmware 2.4.6 and 2.5.1; this does
not physically validate every firmware or installation. Optional fields are
detected by presence rather than firmware number alone. Firmware 2.5.2 and
Trydan Pro master/secondary arrangements remain unverified.

Measured L1 current/voltage entities appear when reported by the charger.
L2/L3 measurements and light controls are not exposed; the latter were removed
because local states were inconsistent. Local brand icons are served by
HA 2026.3 and later.

## Installation

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Carbanog&repository=V2C_trydan&category=integration)

1. Back up HA.
2. Use the button or add `https://github.com/Carbanog/V2C_trydan` in HACS as a
   custom **Integration** repository.
3. Download stable **1.4.0** and restart HA.
4. Open **Settings → Devices & services → Add integration → V2C Trydan**.
5. Enter the charger's local IP address.

Without HACS, download a release and copy only `custom_components/v2c_trydan`
to `/config/custom_components/v2c_trydan`; restart and continue from step 4.
Do not install two implementations using the `v2c_trydan` domain side by side.
Avoid competing controllers/automations sending contradictory commands.

## Updates, beta testing and rollback

IP setup/reconfiguration uses one request with a 10-second HTTP timeout. Normal
polling retains its three-attempt/20-second policy. A command waiting over 10
seconds for the shared connection is rejected **without being sent** and cannot
execute later. Sent writes retain their separate 10-second timeout and are never
retried blindly; a lost acknowledgement can still mean the command executed.
State refreshes may be debounced. These are not guaranteed electrical stop times.

Update through HACS and restart. Do not delete/recreate the integration:
existing IDs, customizations and stored sessions are retained. Use **Reconfigure**
if the IP changes. Reload after firmware upgrades to discover available optional fields.

Future prereleases require explicit selection in HACS. Prefer an isolated test
installation and never let two HA instances govern the same charger.

To roll back, review the actual pause state, disable scheduling if it was enabled,
download **1.3.3** and restart. Disabling/unloading does not automatically resume
charging. Scheduling entities can remain unavailable after rollback; user registry
records are not automatically deleted.

## Entities and configuration

| Group | Contents |
| --- | --- |
| Everyday controls | Pause charge, lock charger and manual current. |
| Session | Session energy, active time and optional reset button. |
| Monitoring | Charging power/partial energy, charge state, house power, cable/charging states. |
| Optional settings | Current limits, dynamic charging/mode, timer and dynamic pause. |
| Optional diagnostics/measurements | Meter, firmware, network, Wi-Fi, raw states, measured L1 voltage/current. |
| Optional scheduling | Mode, current tariff and status; only when enabled. |

New installs keep advanced settings, solar/home-battery data and many diagnostic
entities disabled. Existing entity choices survive updates. Enable what you need
under **Settings → Devices & services → Entities**, including disabled entities
in the filter. Enabling an entity alone does not modify the charger.

Choose your language in the HA profile. Existing entity IDs, customized names
and manually written dashboard text are not automatically renamed.

## Session accounting

**Charge Energy** is the firmware's partial counter. **Session Energy** and
**Session Active Charging Time** accumulate increments across pauses and counter
resets. They do not depend on Octopus and also work with manual charging.

Totals remain after unplug for delayed summaries; the next observed connection
starts a new session. Charger faults do not start a new session on recovery.
State is checkpointed independently of Recorder. An optional reset button
handles exceptional corrections.

Display precision is two decimals; time is stored in seconds. If an older entity
still displays seconds, choose hours in its settings without resetting its total.
Energy erased by the charger while HA was offline cannot be reconstructed.

## Optional charging schedules

A separate, optional module, **disabled by default**, with no helpers or
automations to create. Configure multiple blocks per day, different weekdays,
Peak/Shoulder/Off-peak labels and overnight intervals. Utility hours, holidays
and prices are not assumed or fetched.

In **Configure**, add or edit blocks, choose permitted tariffs and enable the module.
**Save and apply** shows enabled state, blocks and gaps, then requires explicit
confirmation. Overlaps are rejected; unassigned time does not permit charging.

| Mode | Behavior |
| --- | --- |
| Automatic | Permits charging only in selected tariff periods. |
| Charge now | Ignores tariffs until an observed connection followed by unplug. |
| Paused | Latches a stop until another mode is chosen. |

First activation starts Paused. Only `Paused` is written: the policy never
unlocks the charger or changes current/dynamic regulation. While enabled, the
existing pause switch selects Paused when on, and Charge now when off.
Status explains waiting, shows the next window as an attribute, and raises a
**Repairs** warning if an attempted command stays unconfirmed for one minute.

**HA must remain running and connected.** An outage can prevent stopping at a
boundary; an unplug/replug entirely during downtime may go undetected.
The next window previews tariff permission, not a guaranteed vehicle start.
Do not combine with OCPP/Octopus or other charging schedules. Leave dynamic
regulation and electrical protections enabled.

[Full setup, physical-test and rollback guide](https://github.com/Carbanog/V2C_trydan/blob/v1.4.0/docs/scheduling.md).
Physical tariff-boundary and manual-override checks remain necessary in your
installation. No supervised physical verification is claimed by this release.

Optional L1 capabilities are discovered on the first read at setup. Reload the
integration after a firmware update to discover fields newly provided by the charger.

## Blueprints and automations

Optional imports live in [blueprints/automation](blueprints/automation).
They are never automatically installed or enabled.

**Session summary and notifications**

[![Import into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0%2Fblueprints%2Fautomation%2Fsession_summary.yaml)

[View YAML](blueprints/automation/session_summary.yaml). Runs start/end actions
without repeating every OCPP pause. Finish actions can use `session_kwh`,
`session_seconds`, `session_hours`, `session_duration`, `estimated_percent`,
`estimated_cost` and `estimated_range_km`.

The start action can wait several days after connection. Like other HA waits,
it does not survive an HA restart or automation reload; this is not a persistent
notification queue. Update/re-import an existing blueprint to receive fixes.

Example finish action; replace the notification service:
```yaml
action: notify.mobile_app_your_phone
data:
  title: Charging finished
  message: "{{ session_kwh }} kWh · {{ session_duration }}"
```

**High charging power alert**

[![Import into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FCarbanog%2FV2C_trydan%2Fblob%2Fv1.4.0%2Fblueprints%2Fautomation%2Fhigh_power_alert.yaml)

[View YAML](blueprints/automation/high_power_alert.yaml). Runs chosen actions
after a power threshold is exceeded for a configured duration; exposes `measured_power`.

Vehicle capacity, efficiency, price and consumption are optional blueprint inputs.
Battery-added percentages, cost and range are estimates for notifications, not
vehicle-reported SOC or newly created sensors.

## Dashboards

- [Native](dashboards/native.en.yaml): standard HA cards.
- [Mushroom](dashboards/mushroom.en.yaml): requires Mushroom and Mini Graph Card.

Paste the YAML into a manual card and adapt entity IDs to your installation.
The integration never changes your dashboards automatically.

See the [dashboard previews](#at-a-glance) above. Open either image for full size.


## Compatibility actions

New automations should normally target `switch`, `number` and `select` entities.
Compatibility actions remain available: `v2c_trydan.set_intensity`,
`v2c_trydan.set_min_intensity`, `v2c_trydan.set_max_intensity` and
`v2c_trydan.set_dynamic_power_mode`. Supply `config_entry_id` when needed to
select one of multiple chargers.

They do not replace every V2C app setting. Do not change protection-related
current limits, dynamic charging or advanced modes without understanding the installation.

## Diagnostics and limits

One shared poll every **15 s**, a **20 s** read timeout and up to **3 attempts**
for transient failures, separated by **2 s**. Requests are serialized per charger.
Permanent HTTP errors, redirects and invalid snapshots remain visible.
Writes require `OK` and are not blindly repeated.

For a report, enable debug logging in the integration menu, wait for failure and
recovery, then disable logging and download logs/diagnostics. They include read
attempts, elapsed time, latest failure and observed recovery.
Automatic recovery alone does not identify a network root cause.
Known IP, SSID and hardware-ID fields are redacted from diagnostics, but review
all logs and screenshots before publishing.

There is no real vehicle SOC, kilometre charging target, PVPC integration or
automatic price optimization. Scheduling is neither a safety mechanism
nor a guarantee of tariff compliance during HA/network downtime.

## Contributing and HACS readiness

Use [Issues](https://github.com/Carbanog/V2C_trydan/issues) with integration/HA/
firmware versions, reproduction steps and reviewed, privacy-safe diagnostics.
Maintained languages are English, Spanish and French; native wording corrections
are welcome. Add languages when there is demand and someone to maintain them.

[Architecture and development](docs/architecture.md) ·
[HACS catalog readiness checklist](docs/hacs-readiness.md).

Checks include Ruff, pytest, hassfest and HACS. CI also tests actual
HA lifecycle with a mocked charger; this does not replace physical verification.
Default HACS catalog inclusion requires a separate submission and review.

## License and credits

An independent project maintained by [Carbanog](https://github.com/Carbanog),
not affiliated with V2C or Home Assistant. It began from
[Rain1971's work](https://github.com/Rain1971/V2C_trydant) and has evolved with its
own functionality and architecture while retaining that acknowledgement.

[MIT license](LICENSE), with original-author and Carbanog copyright notices
preserved. Thanks to the community and AI tools used during development/review.
Icon provenance is documented in [brand-assets](docs/brand-assets.md).
Optional support is available in **Sponsor this project** in the repository sidebar.
