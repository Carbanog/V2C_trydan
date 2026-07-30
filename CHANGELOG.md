# Changelog

All notable changes to this project are documented here.

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
