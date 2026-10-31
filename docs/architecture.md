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
* `entity.py` owns device metadata, stable unique IDs and common command handling.
* `utils.py` provides defensive, Home Assistant-independent value conversion.
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
   Device lookups are scoped to the config entry, so another entry sharing an
   identifier cannot be selected. Older HA versions use scoped enumeration
   rather than the deprecated global device lookup.
6. The malformed-JSON workaround only inserts the known missing comma before
   `ReadyState`; it does not attempt to guess arbitrary corrupt responses.
7. Session statistics reset only on a new cable connection or an explicit user
   action. Disconnection preserves completed values for delayed automations.
8. Session state is checkpointed outside Recorder. Connection transitions are
   saved immediately; long-running charges are saved at a bounded cadence to
   avoid unnecessary storage writes.
9. Storage additions are backwards compatible. The b4 energy-only checkpoint is
   accepted and extended with active time without discarding accumulated energy.
10. Session time is stored and published natively in seconds. Home Assistant's
    supported duration-unit conversion presents it in hours without weakening
    the accumulator or coupling presentation to persistence.
11. Only charge state `0` proves disconnection; `1` and `2` prove connection.
    Fault/unknown snapshots do not update session baselines or trigger a new
    session on recovery. Existing binary-entity state mapping is unchanged.
12. Successful snapshots contain finite, non-negative core power/counters and
    an integer charge state. Optional/new firmware fields are not required.
13. Writes require `OK` and are not retried because the command may have executed
    before a response was lost. Redirects are not followed for reads or writes.

## Communication failures and recovery

The API preserves the configured three-attempt/20-second read policy. Transport
failures, HTTP 408/429, and HTTP 5xx are retryable. Other non-200 statuses are
reported immediately. Invalid payloads fail without retrying. Cancellation is
propagated, releasing the serialization lock without fabricating an offline poll.

Read diagnostics contain sanitized error categories, status codes, attempt counts,
and monotonic durations. They retain the last failed poll after a successful poll.
The first failed poll starts an observed failure window; successful recovery logs
its elapsed duration and clears the consecutive-failure count. This window can
include polling delays and cannot identify the exact instant of a physical outage.
No response body, full transport exception string, URL, ID, or SSID is logged by
these diagnostics. Home Assistant continues to own entity availability and final
failure logging through `UpdateFailed`.

The integration shares Home Assistant's HTTP client and never closes it. Connection
pooling is retained; disabling keep-alive or changing network timeouts requires
evidence from the recorded failure rather than an assumed transport defect.

## Firmware measurements

L1 current and voltage use additive entity IDs and start disabled. Their sensor
descriptions declare a required API key, checked at platform setup instead of
assuming availability from a firmware version string. Missing keys on old firmware
do not create empty optional entities; reload after a firmware upgrade. These
measurements do not replace the existing current setpoint/reference voltage.

## User-facing extensions

Automation blueprints and dashboard YAML live outside `custom_components` and
are opt-in examples. The integration never creates automations, helpers, or
Lovelace resources on behalf of the user. Vehicle capacity, charging efficiency,
energy price, and estimated range remain in those optional layers because they
describe a vehicle or tariff rather than the charger hardware.

Advanced charger settings remain represented as entities for capable users, but
are categorized as configuration and disabled by default when accidental changes
could conflict with V2C app schedules, load protection, or OCPP control.

## Optional scheduling (1.4 beta)

Scheduling is a local opt-in policy, not firmware telemetry or a change to the
HTTP API. The coordinator exposes an optional manager reference but continues
to own reads and session accumulation. With scheduling disabled, no manager,
timer, policy store load, extra entities or scheduling writes are created.

* `scheduling/policy.py`: validates weekly wall-clock intervals and makes pure
  decisions. Unknown time is denied; overlaps including week wrap are rejected.
* `scheduling/controller.py`: serializes decisions and user intent, checkpoints
  before issuing a single command, and reconciles pending writes with reads.
* `scheduling/ha.py`: Store, coordinator/clock subscriptions, task cancellation
  and entity listeners. Scheduling state uses a separate storage key/version.
* `scheduling/alerts.py`: monotonic 60-second debounce and deduplication for
  unresolved-command Repairs warnings. No network IO or automatic retries.
* `scheduling/presentation.py`: localized summaries using HA translation resources.
* `config_flow.py`: edits an options draft with native HA forms; only Save
  shows a summary and requires explicit confirmation before committing it.
  Navigation actions are consumed before draft validation or mutation; Back
  ignores the current screen, Cancel discards the whole edit. UI-only fields
  never enter saved options, and no form sends charger commands directly.
  Options changes reload the entry to rebuild optional entities.

The next tariff window is an attribute, calculated off the event loop at most
once per minute while Auto waits. The bounded UTC-minute search evaluates local
time, handling real DST gaps/folds. It previews tariff permission, not actuation.

Only `Paused` is written, through the same API lock used by manual controls.
An HA pause-switch action selects Paused; resume selects Charge now. An
unexpected new pause from another controller latches Paused. The policy never
unlocks the charger or disables its own Timer. Unsupported concurrent OCPP/app
schedulers must be disabled by the user before testing this feature.

Mode and pending intent are persisted before actions. Failed/ambiguous writes
are not repeated on every clock/poll event. A fresh read can confirm them;
otherwise the user must inspect the state and explicitly select a mode to retry.
Disabling/unloading never automatically resumes a paused charger. HA/network
outages cannot enforce boundaries, and an unplug/replug entirely during an
outage cannot reliably be detected. See the beta guide for testing and rollback.

## Development

Create a virtual environment and run:

```bash
python -m pip install -r requirements_test.txt
ruff check .
ruff format --check .
pytest
```

GitHub Actions additionally runs Home Assistant `hassfest` and HACS validation.
Every behavior change should include focused tests. API and session-state behavior
belong in fast unit tests; config flows, entity setup, registry migrations, and actions
should use Home Assistant integration tests as coverage is expanded.

`tests/fixtures` contains explicitly anonymized, recorded firmware 2.4.6/2.5.1
responses. Local HTTP tests use an aiohttp test server on loopback, never a real
charger. Unit tests cover payload/acknowledgement validation, permanent versus
transient HTTP failures, outage/recovery diagnostics, serialization, cancellation,
and fault-state session preservation. These tests are not a full HA installation
test or proof of a physical network fix.

## Compatibility policy

Public entity unique IDs, config-entry data, and action names are persisted user
interfaces. Changes to them require an explicit migration. Removing stable
entities requires a documented deprecation period. Experimental beta entities
may be removed before stable release only with targeted registry cleanup and a
documented reason, as done for the unreliable b3/b4 light controls.
