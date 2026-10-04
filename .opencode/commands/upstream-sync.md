---
description: Incrementally merge upstream commits with conflict checkpoints and local ESPHome validation
agent: orchestrator
---

Run the EspControl upstream synchronization workflow.

Requested mode: $ARGUMENTS

## Modes

- No mode or `start`: inspect the current branch and merge state. If no merge is in progress, prepare a dedicated sync branch and freeze the upstream target. Merge upstream first-parent commits oldest-first with normal `git merge --no-ff --no-edit`, committing each clean merge. Stop at the first conflict or new validation blocker.
- `resolve`: review and resolve only the current merge conflict. Ask the user about ambiguous behavior or any new shared-source change. Validate the resolution, commit it, and stop immediately after the commit. Do not begin the next merge.
- `continue`: resume from the current clean state after the user explicitly asks to continue. Merge clean commits until the next conflict or blocker, then stop.

## Rules

- Work on a dedicated branch; never switch away from the user's current branch without explaining why.
- Preserve existing user changes. Inspect `git status` before changing anything. Never use `git reset --hard`, `git clean`, or an implicit merge abort.
- Use merges, not cherry-picks, so upstream ancestry remains intact.
- Freeze the upstream target and ordered commit list with `git rev-list --reverse --first-parent` before processing it. Do not silently fetch a newer target during the run.
- Stop immediately at the first conflict. Do not resolve, stage, abort, or commit that conflict until the user has reviewed the conflict and authorized the resolution.
- If the user says to pause after a resolution, stop immediately after the merge commit. Do not inspect or start the next commit.
- Never push automatically.
- Treat generated assets, manifests, fixtures, and device documentation as generated outputs. Merge source intent, then regenerate them with the repository workflow; do not hand-merge minified bundles or hashes.
- Preserve JC4827W543R support, device-specific hardware configuration, profile/catalog entries, and existing unsupported-feature decisions unless the user explicitly changes them.
- Before any shared-source behavior change, explain why it belongs across devices, identify affected devices, and ask for explicit approval. After approval, preserve existing behavior and validate the target plus affected devices.
- Use the repository's local ESPHome wrapper for validation: `scripts/local_esphome.py` with the pinned version from `.github/esphome.env`. Compile only unless the user explicitly requests flashing. Never read, print, create, copy, or commit secrets.
- Validate configuration, firmware compilation, host tests, web checks, and physical display/touchscreen behavior as separate results. Do not claim compilation or hardware validation from configuration checks alone.
- Preserve the actual firmware variant during validation. In particular, do not add embedded web assets to a device whose product profile uses hosted JavaScript merely to make a local wrapper work.
- Run focused checks after each meaningful resolution. Do not fix unrelated pre-existing failures without approval; report them separately.
- Before committing, inspect the staged diff and status. Stage only intended merge resolutions and generated outputs. Never commit secrets or temporary build wrappers.
- If validation fails because of an environment limitation, report the exact limitation and do not label the validation as passed. If the failure indicates a source or configuration defect, stop for review rather than making an unrelated workaround.

## Required report

For every run, report:

- Current branch, upstream target, merge state, and exact commit count completed and remaining.
- Each clean merge commit with its upstream commit and title.
- At the stopping point, the conflicting paths, conflict categories, upstream/local intent, and the smallest reasonable resolution.
- Validation commands and separate results for configuration, compilation, tests, and hardware.
- Any pre-existing failures or environment blockers.
- Whether the working tree is clean, conflicted, staged, or committed.
