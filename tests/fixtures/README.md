# Recorded charger responses

These are **test fixtures**, based on user-supplied HTTP responses from firmware
2.4.6 and 2.5.1. Hardware ID, SSID, and IP have been replaced with examples and a
documentation-only address. They are never loaded by the integration.

The duplicate `FirmwareVersion` in the 2.4.6 fixture intentionally preserves the
original firmware behavior. The 2.5.1 idle and charging fixtures exercise the
new measurements without assuming they are available in earlier firmware.
