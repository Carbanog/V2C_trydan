# Changelog

All notable changes to this project are documented here.

## 1.3.0b6

### Changed

* New session-time entities now suggest hours with two decimals while retaining
  seconds as their native and persisted precision.
* The session-summary blueprint accepts duration sensors displayed in seconds,
  minutes, hours, days, or milliseconds and exposes a readable
  `session_duration` value such as `2 h 15 min`.
* Mushroom dashboard summaries now render accumulated time as hours and minutes.
* Both READMEs now provide direct blueprint-import buttons, source locations,
  configuration guidance, available template variables, and copyable
  notification examples.

### Compatibility

* Home Assistant intentionally retains the unit selected when an entity was
  first registered. Users upgrading from b5 can change the session-time unit
  from seconds to hours in entity settings without resetting state or history.

## 1.3.0b5

### Added

* Persistent session active-charging time, accumulated across the same OCPP/app
  pause resets as session energy and retained after disconnection.
* Active-time variables in the session-summary blueprint and matching entries in
  all dashboard examples.

### Changed

* Session energy now suggests two display decimals while retaining full internal
  precision.
* The raw firmware charge-time sensor starts disabled on new installations
  because it describes only the current charging segment.
* The optional reset button now resets both accumulated session statistics.

### Removed

* Experimental charger and logo light controls from b3/b4. Physical testing on
  firmware 2.4.6 showed that their local API state was not reliable or
  synchronized with the V2C app. Upgrade cleanup targets only those two beta
  registry entities.

### Internal

* Generalized the pure session state machine and migrated b4 energy checkpoints
  additively, without losing their accumulated energy.
* Session storage is deleted only when its config entry is permanently removed.

## 1.3.0b4

### Added

* Persistent whole-session energy that accumulates charger counter segments
  across OCPP/app pauses, remains visible after disconnection, and resets on the
  next cable connection.
* Optional manual session reset button with a safe current-counter baseline.
* Enabled meter-problem binary sensor for straightforward alerts.
* Importable session-summary and high-power-alert automation blueprints.
* Native Home Assistant and optional Mushroom/Mini Graph dashboard examples.

### Changed

* Reduced UI and Recorder noise for new installations by disabling solar,
  home-battery, duplicated readback, installation, advanced dynamic-control, and
  identifying diagnostic entities by default.
* Classified writable device settings as configuration entities. Existing
  entity-registry choices remain untouched during upgrades.
* Rewrote both READMEs around the current architecture, session semantics,
  safe OCPP/dynamic-charging behavior, optional blueprints, and dashboards.

### Internal

* Isolated session accumulation in a Home Assistant-independent state machine
  with focused coverage for counter resets, disconnects, restarts, invalid
  persisted data, and manual resets.
* Persisted compact session checkpoints independently of Recorder while limiting
  storage writes during long charges.

### Fixed

* Rejected non-finite charger numbers so `NaN` or infinity cannot become invalid
  Home Assistant sensor or persisted session states.
* Normalized the harmless shared-HTTP-session shutdown race instead of reporting
  it as an unexpected coordinator exception.

## 1.3.0b3

### Added

* Optional charger-light and dimmable logo-light controls for firmware that
  exposes `LightLED` and `LogoLED` through the local read API.
* Writable timer and dynamic-modulation pause switches when those capabilities
  are present in `RealTimeData`.
* Human-readable charge-state faults and meter communication errors.

### Changed

* Optional LED values are refreshed once per minute and cached between the
  normal 15-second polls. Their failure cannot make core charger data
  unavailable, protecting PLC and weak Wi-Fi installations.
* Legacy numeric diagnostic sensors retain their historical statistics metadata
  for upgrade compatibility but are disabled by default on new installations;
  a separate enum sensor provides readable meter errors.

### Fixed

* Restored the charge-time sensor's `total_increasing` state class used by
  releases before the refactor and by Home Assistant's official integration.

## 1.3.0b2

### Fixed

* Restored the Wi-Fi signal sensor's `measurement` state class so Home
  Assistant can continue its existing long-term statistics after upgrading.

## 1.3.0b1

First public beta of the 1.3.0 refactor. Install it only on a test Home
Assistant instance until the hardware migration and charger controls have been
verified against a physical V2C Trydan.

### Added

* Reconfiguration flow for changing a charger's IP from Home Assistant.
* Privacy-safe config-entry diagnostics.
* Stable hardware-based device and entity identifiers with migration of
  identifiers created by version 1.2.2 and earlier.
* Optional charger selection for compatibility actions in multi-charger setups.
* Automated API tests, Ruff checks, and a Python quality workflow.
* Architecture and maintenance documentation.

### Changed

* Centralized HTTP reads and writes in a typed asynchronous API client.
* Serialized requests per charger to protect PLC and weak Wi-Fi links.
* Delegated availability and retry logging to Home Assistant's data coordinator.
* Updated GitHub checkout actions and removed the redundant `aiohttp` manifest
  requirement because Home Assistant provides it.
* Disabled duplicate diagnostic state sensors by default while preserving
  existing registry entries.

### Fixed

* Service metadata now uses Home Assistant-compatible lowercase field names;
  the legacy `DynamicPowerMode` action parameter remains accepted.
* String values such as `"0"` are no longer interpreted as enabled switches.
* Invalid or absent number values no longer report fabricated defaults.
* Write responses containing `ERROR` are handled consistently on every control.
* The malformed JSON repair is narrow, deterministic, and preserves the last
  duplicate JSON key as defined by Python's decoder.
* Compatibility actions no longer silently control the last configured charger.
