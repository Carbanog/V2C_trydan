# Optional charging schedules — 1.4.0b2 beta

Stable production release remains **1.3.3**. This opt-in beta does not update
charger firmware or change dynamic load protection. Install explicitly through
HACS's re-download/version selection on a test HA only, enabling prereleases
there if necessary and select **1.4.0b2**, then restart. Back up first. Do not enable beta updates on
production or let two HA instances send commands to the same charger.

## Configure

Open **Settings → Devices & services → V2C Trydan → Configure**. Changes remain
a draft until **Save and apply**; cancelling discards the draft.

1. Add blocks: start days, start/end time, and Peak / Shoulder / Off-peak tariff.
2. In Settings, enable scheduling and select allowed tariffs (none is permitted).
3. Save opens a summary of enabled state, blocks, allowed tariffs and uncovered
   intervals. Review it and explicitly confirm to apply; cancelling does not
   change the existing configuration. To edit a block, remove it and add a replacement.

There are no assumed utility hours, prices or automatic holidays. Up to 100
blocks may cover different days and multiple intervals per day. Overlaps are
rejected, including across midnight and Sunday/Monday. Unassigned time is denied.
Times use HA's local timezone, with minute precision and an inclusive start /
exclusive end. An earlier end crosses midnight from the selected start day.
**00:00–00:00** is a full day; other equal endpoints are invalid. Repeated local
hours use the same tariff; skipped local hours are not replayed.

Only three new entities appear when enabled: **Charging schedule mode**,
**Current tariff**, and **Scheduling status**. First activation starts **Paused**;
explicitly select Automatic. Subsequent starts restore persisted intent.

* Automatic pauses outside allowed blocks and permits charging inside them.
* Charge now ignores tariff blocks until an observed physical unplug, then
  returns to Automatic. It can be armed before connection, expiring only after
  connection then unplug. Pauses/faults/network failures do not expire it.
* Paused is a latched stop until another mode is explicitly selected.

When enabled, the existing pause switch selects Paused when turned on, and
Charge now when turned off. An unexpected new charger pause latches Paused;
it may originate from a user, another controller or firmware. No automatic
assumption is made about who requested it.

## Boundaries and failures

Only `Paused` is written. The policy never disables `Dynamic`, changes current,
unlocks `Locked` or turns off `Timer`. Locks, active device timers, faults and
incomplete snapshots prevent resuming. Disable conflicting V2C app timers,
OCPP and other charging automations before enabling this policy; closing an
app is not enough. Dynamic regulation and electrical protections must stay on.

Mode and pending intent are stored separately from session totals. An unconfirmed
command is not blindly repeated: a later read may confirm it. Otherwise review
the charger and explicitly select a mode to retry. A failed checkpoint prevents
the write. Restart and recovery re-evaluate the current local time.

In b2, an attempted command still unconfirmed after at least 60 seconds raises
one warning in **Settings → System → Repairs**. Confirmation, observed unplug
or scheduler unload clears it. It does not configure mobile push notifications
or detect incidents while HA is stopped. It never blindly retries the command.

Scheduling status now has a **Next allowed tariff start** attribute while Auto
is waiting. It is empty when already allowed, outside Auto or when no permitted
window exists. It previews tariff permission, not a guaranteed vehicle start;
locks, faults and availability still matter. There is no additional sensor.
Generated summaries follow HA's language. UI and alert translations cover
English, Spanish and French.

HA must remain running and connected to enforce boundaries. During downtime
the charger keeps its last state; timely stopping is **not guaranteed**. Polling
can allow brief charging immediately after plugging in. An unplug/replug entirely
during an outage cannot be identified reliably. This is not a safety mechanism
or a guarantee of tariff compliance.

## Beta checks and rollback

Test disabled behavior first, then short allowed/denied blocks, manual pause,
Charge now followed by unplug, restart in each mode, night/weekend intervals,
overlap rejection and safe communication recovery. Check actual charging and
session totals, not only the selector. Physical operation has not yet been
validated on your installation. Software tests use explicit fake charger data.

Disable scheduling in options and Save to remove its subscriptions/entities;
this does not automatically resume the charger. Review the current pause state.
To roll back, re-download **1.3.3** in HACS and restart. Session storage is unchanged;
scheduler state is separate. Beta-only entities may remain unavailable in the
registry after rollback; user registry records are not automatically deleted.

See the [detailed Spanish test guide](scheduling.es.md) for the full checklist.
