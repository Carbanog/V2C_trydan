# Architecture

V2C Trydan is a local-polling Home Assistant integration. Its design favors
predictable behavior on PLC and weak Wi-Fi networks over request throughput.

## Modules and responsibilities

* `api.py` owns HTTP, timeouts, retries, response validation, the narrow firmware
  JSON repair, and request serialization. It has no Home Assistant dependency.
* `coordinator.py` translates API failures into Home Assistant update failures and
  performs one shared poll for all entities. It also owns the persistence boundary
  for local charging-session state.
* `session.py` is a Home Assistant-independent state machine that accumulates raw
  energy and active-time counter deltas across pauses and resets. It contains no
  I/O.
* `entity.py` owns device metadata, stable unique IDs, common command handling,
  and defensive value conversion.
* Platform modules only describe entities and map coordinator values to Home
  Assistant concepts.
* `config_flow.py` validates new or changed addresses and identifies the charger
  by its hardware ID.
* `diagnostics.py` exposes support data while redacting network and identity
  fields.
* `__init__.py` controls the config-entry lifecycle, compatibility actions, and
  the one-time migration from historical IP-based registry identifiers.

## Important invariants

1. Only `V2CTrydanApi` constructs charger URLs or sends HTTP requests.
2. All requests for one charger pass through the same asynchronous lock.
3. A read failure never fabricates a sensor value; coordinator entities become
   unavailable.
4. A command is followed by a coordinated refresh, so all related entities
   observe the same device snapshot.
5. New registry identifiers use the hardware ID. The migration preserves
   existing entity IDs, names, areas, and dashboard references.
6. The malformed-JSON workaround only inserts the known missing comma before
   `ReadyState`; it does not attempt to guess arbitrary corrupt responses.
7. Session statistics reset only on a new cable connection or an explicit user
   action. Disconnection preserves completed values for delayed automations.
8. Session state is checkpointed outside Recorder. Connection transitions are
   saved immediately; long-running charges are saved at a bounded cadence to
   avoid unnecessary storage writes.
9. Storage additions are backwards compatible. The b4 energy-only checkpoint is
   accepted and extended with active time without discarding accumulated energy.

## User-facing extensions

Automation blueprints and dashboard YAML live outside `custom_components` and
are opt-in examples. The integration never creates automations, helpers, or
Lovelace resources on behalf of the user. Vehicle capacity, charging efficiency,
energy price, and estimated range remain in those optional layers because they
describe a vehicle or tariff rather than the charger hardware.

Advanced charger settings remain represented as entities for capable users, but
are categorized as configuration and disabled by default when accidental changes
could conflict with V2C app schedules, load protection, or OCPP control.

## Development

Create a virtual environment and run:

```bash
python -m pip install -r requirements_test.txt
ruff check .
pytest
```

GitHub Actions additionally runs Home Assistant `hassfest` and HACS validation.
Every behavior change should include focused tests. API and session-state behavior
belong in fast unit tests; config flows, entity setup, registry migrations, and actions
should use Home Assistant integration tests as coverage is expanded.

## Compatibility policy

Public entity unique IDs, config-entry data, and action names are persisted user
interfaces. Changes to them require an explicit migration. Removing stable
entities requires a documented deprecation period. Experimental beta entities
may be removed before stable release only with targeted registry cleanup and a
documented reason, as done for the unreliable b3/b4 light controls.
