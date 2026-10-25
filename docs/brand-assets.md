# Brand asset provenance

`custom_components/v2c_trydan/brand/icon.png` is an unmodified copy of the V2C
icon in the Home Assistant brands repository:

* Source: https://github.com/home-assistant/brands/blob/6cc9c84d1e98635f04533bcbd2146ac6930feed7/core_integrations/v2c/icon.png
* Retrieved: 2026-10-25
* SHA-256: `698bb85ac9c75de1de7275d231332ddb42f8592ea5d739d7a8055e4fb5bf39a1`

The V2C name and image identify the supported charger. Trademarks remain the
property of their respective owners; their use does not imply endorsement by
V2C or Home Assistant. This is an independent custom integration, not the
official Home Assistant V2C integration. See the upstream
[trademark notice](https://github.com/home-assistant/brands/blob/6cc9c84d1e98635f04533bcbd2146ac6930feed7/README.md#trademark-legal-notices).

Home Assistant 2026.3 and later can serve local integration images from `brand/`.
HACS validates the local icon rather than requiring a separate entry for the
`v2c_trydan` domain in the upstream brands repository.

## Category compatibility

The documented category is `energy.ev_charging`, but on 2026-10-25 the image
used by `home-assistant/actions/hassfest@master` rejects the `categories` key
even though the development schema accepts it. Categories are optional for
custom integrations, so the manifest omits this key until the published
validator supports it. HACS may therefore still show a category warning.
Neither validator is disabled or bypassed.
