# EspControl Display Port

## Goal

This repository is being updated to support our display and touchscreen. The
known-working implementation is in `~/gitsource/office-touchscreen`; use it as
the reference for the display hardware, touchscreen hardware, pin assignments,
and working ESPHome configuration.

This repository does not support that hardware yet. Add support progressively
in vertical slices, keeping each change focused and leaving the existing device
support working.

Hardware: https://devices.esphome.io/devices/guition-jc4827543c/

## Development Guidance

- Compare hardware and configuration changes with the known-working project before implementing them.
- Keep hardware support, UI behavior, and unrelated cleanup separate.
- Validate configuration and compilation where possible.
- Distinguish compile validation from testing on the physical display and touchscreen.
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
