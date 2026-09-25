# EspControl Device Integration

## Goal

Integrate display devices as first-class EspControl devices. The current device
effort is the Guition JC4827W543R, documented at
https://devices.esphome.io/devices/guition-jc4827543c/.

The goal is complete device integration through device addition and
configuration, using EspControl's existing shared capabilities wherever they
fit. Device-specific hardware and presentation needs belong in that device's
configuration and metadata when possible. Keep universal behavior consistent
across the supported devices; device integration is not a general redesign of
that behavior.

## Development Guidance

- Follow the repository's existing device patterns and use device-specific
  configuration for hardware details such as pins, display geometry, touch,
  fonts, layout, and defaults.
- Keep the device's manifest/catalog metadata, ESPHome packages, and generated
  device files in sync using the repository's existing generation workflow.
- Before implementing a shared-source behavior change, explain why the
  capability belongs across devices, identify the affected behavior/devices,
  and ask the human developer whether they agree. Wait for explicit agreement
  before proceeding. If agreement is not given, keep the solution device-
  specific or pause for direction.
- After an approved shared change, preserve existing device behavior and
  validate the target device plus other affected devices.
- Validate configuration and compilation where possible. Report compile
  validation separately from testing on the physical display and touchscreen.
- Keep credentials and other secrets out of tracked files.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `shahvirb/espcontrol-jc4827w543r`.
See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default canonical triage labels on GitHub. See
`docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository. See `docs/agents/domain.md`.
