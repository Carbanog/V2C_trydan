# Architecture

V2C Trydan is a local-polling Home Assistant integration. Its design favors
predictable behavior on PLC and weak Wi-Fi networks over request throughput.

## Modules and responsibilities

* `api.py` owns HTTP, timeouts, retries, response validation, the narrow firmware
  JSON repair, and request serialization. It has no Home Assistant dependency.
* `coordinator.py` translates API failures into Home Assistant update failures and
  performs one shared poll for all entities.
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
7. Optional firmware capabilities are detected through read-only endpoints,
   refreshed less frequently, and cached. An optional failure never invalidates
   the core `RealTimeData` snapshot.

## Development

Create a virtual environment and run:

```bash
python -m pip install -r requirements_test.txt
ruff check .
pytest
```

GitHub Actions additionally runs Home Assistant `hassfest` and HACS validation.
Every behavior change should include focused tests. API behavior belongs in
fast unit tests; config flows, entity setup, registry migrations, and actions
should use Home Assistant integration tests as coverage is expanded.

## Compatibility policy

Public entity unique IDs, config-entry data, and action names are persisted user
interfaces. Changes to them require an explicit migration. Removing an entity or
action requires a documented deprecation period rather than hiding or silently
replacing it.
