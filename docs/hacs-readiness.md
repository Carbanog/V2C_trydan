# HACS catalog readiness

This project is already installable through HACS as a custom repository. Being
included in the default catalog is a separate process, not an automatic result
of using HACS badges or passing CI. No catalog submission is authorized by this
document. Review the live requirements again before submitting.

## Baseline checked on 2026-10-31

* Public, non-archived GitHub repository, enabled issues, description and topics.
* One runtime integration under `custom_components/v2c_trydan/`; valid manifest
  and root `hacs.json`.
* Local brand icon, with source and trademark notes in [brand-assets.md](brand-assets.md).
* MIT license with original and current-author notices preserved.
* Stable GitHub release **1.3.3** retained as latest; **1.4.0b4** is a prerelease.
* Independent domain `v2c_trydan`, not the built-in `v2c` domain. This is not a
  test distribution of Home Assistant core's V2C integration.
* README coverage in English, Spanish and French; install/update/rollback,
  diagnostics, limitations, opt-in extensions and credits are documented.
* Python checks, hassfest and HACS validation are enabled. Beta scheduling also
  has real-HA lifecycle tests with a mocked charger, not physical certification.

The optional `categories` manifest key is deferred because the published
hassfest image rejected it when last checked. No check was disabled to hide
that incompatibility; see [brand-assets.md](brand-assets.md). Recheck current
validators before changing the manifest. Do not add an ignore to force acceptance.

## Before advertising scheduling as stable

- [ ] Confirm physical pause/resume at an allowed/denied tariff boundary.
- [ ] Confirm Charge now, unplug reset, manual pause and HA restart behavior.
- [ ] Review safe network-failure recovery and unresolved-command reporting.
- [ ] Obtain owner approval to merge/promote the beta; do not promote just to
      satisfy catalog expectations.
- [ ] Update all README release tables/import buttons, changelog and release notes.
- [ ] Run all candidate checks without errors or ignored validations.
- [ ] Publish an explicitly approved stable release including the validated code
      and documentation, retaining the previous version for rollback.

## Catalog submission — only after explicit approval

1. Re-read HACS inclusion and integration requirements below. Check domain
   conflicts, manifest, brand assets, repository metadata, license and release.
2. Confirm that the README distinguishes released stable behavior from experiments.
   Do not claim universal hardware support, official affiliation, or HACS acceptance.
3. Submit a separate editable PR to `hacs/default`, adding the repository to the
   integration list in alphabetical order and completing the required template.
4. Address maintainer feedback. The HACS team decides inclusion; passing tests
   and having additional features do not guarantee approval.

No country restriction is assumed: scheduling uses user-defined weekly hours,
not a Spanish utility feed. If the integration becomes country-restricted,
review HACS's country metadata requirement before submitting.

## Authoritative references

* [Default repository inclusion](https://hacs.xyz/docs/publish/include/)
* [Integration repository requirements](https://hacs.xyz/docs/publish/integration/)
* [HACS validation action](https://github.com/hacs/action)
* [HA integration brands](https://contributors.home-assistant.io/core/integrations/brands/)
* [MIT license](https://opensource.org/license/mit)
