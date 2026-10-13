---
description: Safely synchronize one frozen upstream target with conflict review, regeneration, and separate validation gates
agent: orchestrator
---

Run the EspControl upstream synchronization workflow. `$ARGUMENTS` selects the
mode; an empty argument is the read-only `inspect` mode.

## Modes

- `inspect` (default): report branch, worktree, merge state, persisted plan, and
  available upstream information. Do not fetch, switch, merge, regenerate,
  validate, stage, commit, abort, reset, clean, or write the plan.
- `start [remote/ref]`: create or reuse a dedicated sync branch, fetch the
  requested upstream ref once, freeze its full target SHA and first-parent
  ancestry, inspect the incoming diff, and perform exactly one target merge.
  Stop for shared-source approval, a conflict, a regeneration problem, or a
  validation failure.
- `resolve`: inspect and resolve only the current reviewed merge conflict. Run
  focused checks, commit the validated merge, and stop. Never begin another
  merge.
- `continue`: resume the persisted attempt on the same branch. Verify the plan,
  `HEAD`, `MERGE_HEAD`, and frozen target first; then resume regeneration,
  validation, or an uncommitted merge. In `single` strategy it can only finish
  the one frozen target. In `fallback` strategy it may advance to the next
  already-approved checkpoint after the previous one is committed. Do not
  fetch, recompute the target, or invent a checkpoint.
- `fallback approved`: only after the user explicitly approves abandoning the
  single-target attempt. Safely abort the current merge after the abort gate,
  then use only a few checkpoints already selected from the frozen first-parent
  path. Validate and commit each checkpoint; stop after any resolution commit
  and wait for `continue`.

## Non-negotiable safety

- Read [Working Tree Rules](../../dev-docs/working-tree-rules.md) and the
  repository `AGENTS.md` before changing Git state. The sync proposal is not
  blanket approval for shared behavior: before incorporating an incoming change
  to shared firmware, web, product, or configuration behavior, explain why it
  belongs across devices, name affected devices/behaviors, and obtain explicit
  approval. Treat an unknown shared behavior found during conflict resolution as
  unapproved and stop.
- Start with `git status --short --branch`, `git diff`, and merge-state checks.
  Preserve existing user changes and existing Git operations. A dirty tree,
  rebase/cherry-pick, or unrelated merge is a stop condition; ask the user to
  preserve or finish it rather than stashing, resetting, cleaning, or aborting
  it. Never silently use `git reset --hard`, `git clean`, `git restore`, or
  `git merge --abort`.
- Explain why the current branch must be left and name the dedicated sync branch
  before switching. Reuse a branch only when the persisted plan proves that its
  starting branch/HEAD, frozen target, and sync branch match this attempt. Never
  attach a new attempt to an unexplained existing branch.
- Keep the durable plan outside the worktree:
  `PLAN=$(git rev-parse --git-path upstream-sync-v2.json)`. Do not add it to Git,
  put secrets in it, or replace it with an ad-hoc script. Record at least the
  starting branch and full HEAD, sync branch, upstream remote/ref, frozen target
  SHA, base SHA, complete first-parent step list, fallback checkpoints,
  proposed and approved checkpoint list, strategy, approved shared-behavior
  scope, phase, every command/result, and merge commits. Before each merge also
  record a pre-merge snapshot containing `HEAD`, clean status, staged/unstaged
  paths, and the empty or explicitly identified merge-owned edits. Update the
  plan before and after every state-changing step; if it cannot be updated,
  stop.
- On `resolve`, `continue`, or `fallback`, verify the current branch, `HEAD`,
  `MERGE_HEAD` (when applicable), plan phase, and frozen target against the plan.
  Any inconsistency stops the run. A missing plan is not permission to infer
  state from reflogs or fetch again.
- Freeze the target immediately after the one permitted fetch. Resolve the
  remote/ref to a full commit SHA and capture the first-parent list with
  `git rev-list --first-parent --reverse <base>..<target>`. The target and list
  never move during this attempt. Do not count that list as completed merges:
  report `upstream commit count` separately from `integration checkpoint count`.
  The default strategy has one integration checkpoint: the target merge.
- Every merge, including a clean merge and every fallback checkpoint, is
  `git merge --no-ff --no-commit <frozen-sha>`. Validate and inspect shared
  behavior before `git commit`; this deliberately leaves a clean merge
  uncommitted until it passes the same gate as a conflict resolution.
- Preserve the JC4827W543R device, hardware-specific configuration, manifest and
  catalog entries, hosted-JavaScript product variant, and existing unsupported
  feature decisions. Never add embedded web assets merely to make a local check
  convenient. Use the pinned local ESPHome wrapper and never read, print,
  create, copy, stage, or commit credentials or other secrets.
- Do not repair unrelated failures or add workarounds. Record pre-existing and
  environment failures separately. Never push, open/update a PR, or claim
  physical hardware validation automatically.

## `start`: prepare, inspect, and merge once

1. **Preflight.** Run the read-only inspection commands and inspect any existing
   plan. Require a clean worktree and no `MERGE_HEAD`, `CHERRY_PICK_HEAD`, or
   `REBASE_HEAD`; otherwise stop without changing state. If the current branch
   is not the plan's verified dedicated branch, explain the switch and create a
   short-lived branch from the recorded starting `HEAD`. Write the initial plan
   before fetching.
   **Done when:** the dedicated branch is verified, the worktree is clean, no
   unrelated operation is active, and the plan records the starting state.
2. **Freeze.** Fetch only the selected remote/ref (default to the repository's
   configured upstream target after showing it to the user), resolve its full
   commit SHA, record the base and complete first-parent list, and record the
   target's first-parent ancestry. Do not fetch again during this plan.
   **Done when:** the plan contains an immutable target SHA, base SHA, ordered
   list/count, and remote/ref; no later step uses a moving ref name.
3. **Inspect incoming intent.** Review `git log --first-parent`, the summary, and
   the full diff from base to target. Classify source changes versus generated
   outputs and identify shared behavior, device-specific behavior, generated
   files, web delivery/variant changes, and conflicts likely to occur. Ask for
   explicit approval for each incoming shared behavior scope before merging;
   sync initiation itself is not approval. Record the approved scope or stop.
    **Done when:** every shared behavioral change is classified with affected
    devices and explicitly approved, or the entire merge is paused. The frozen
    target is merged as a whole; never silently exclude an unapproved change.
    Exclusion requires an explicitly approved revised target/strategy and a new
    freeze, not filtering this merge.
4. **Merge the frozen target.** Record the phase and pre-merge snapshot, then
   run exactly one `git merge --no-ff --no-commit <target-sha>`. If it conflicts,
   do not stage, resolve, abort, or commit: record `MERGE_HEAD`, unmerged paths,
    conflict categories, both intents, and the smallest candidate resolution,
    then stop for `resolve`. If clean, use the common commit gate below; a clean
    merge is still uncommitted until focused and full checks pass.
   **Done when:** the single target merge is either paused for conflict review or
   is cleanly uncommitted with its result recorded in the plan.

## Regeneration and validation gates

After a clean merge or an authorized resolution, use
[Source of Truth](../../dev-docs/source-of-truth.md), [Devices and Builds](../../dev-docs/devices-and-builds.md),
and the relevant [playbook](../../dev-docs/playbooks/README.md). Regenerate
authored-source outputs only; never hand-edit generated files. Use this order
when the changed sources require it:

```bash
python3 scripts/generate_device_manifest.py
python3 scripts/build.py all
python3 scripts/generate_device_slots.py
python3 scripts/check_product_snapshot.py --update
```

Run only the applicable generators, and record why each was or was not run. For
example, `product/v2/device_catalog.json` uses the manifest generator;
product/entity, contract, icon, translation, device, and web sources use their
`python3 scripts/build.py <command>` generator; device-slot changes follow the
manifest generator; and product-model source changes use the snapshot update.
The source-of-truth table is authoritative when the incoming diff changes.

Use the normal focused task aliases; their declared inputs make their result
cache safe. Reserve `--no-cache` for final profile reruns or a result whose
freshness is genuinely in doubt: `python3 scripts/check_tasks.py run <profile>
--no-cache` (or the equivalent `npm run` alias with `-- --no-cache`). Do not
delete shared caches as a workaround.

Record these as separate results, first focused and then full:

| Gate | Focused evidence | Full evidence |
| --- | --- | --- |
| Configuration/generated | Applicable generator `--check` commands and `npm run check:config` | `npm run check:all -- --no-cache` |
| Compile | Affected `devices/<slug>/dev.yaml` with `python3 scripts/local_esphome.py ... compile`; verify `.github/esphome.env` pin | Every affected device, then the Docker matrix in `.github/workflows/firmware-compile.yml` when that workflow is explicitly run; otherwise record the matrix as not run |
| Host | Relevant host task from `dev-docs/check-matrix.md` (for example `npm run test:firmware`) | `npm run check:fast -- --no-cache` |
| Web | `npm run check:web-smoke`, `npm run check:web-asset-manifest`, and browser smoke when web paths changed | `npm run check:all -- --no-cache` plus `npm run docs:build` |
| Hardware | Physical display/touchscreen behavior only after an explicitly requested flash/test; record device, firmware, and result | Test every affected device separately; a compile is not hardware evidence |

Keep configuration, compile, host, web, and hardware statuses distinct. A
missing Docker daemon, pinned ESPHome CLI, browser, or physical device is an
 environment/not-run result, not a pass. A required automated check or compile
 that cannot run blocks commit and completion; hardware not run remains separate.
 Stop on a source defect; do not make an unrelated workaround. The local compile
 path is the pinned wrapper documented
in [Add or Change a Supported Device](../../dev-docs/playbooks/add-supported-device.md):

```bash
python3 scripts/local_esphome.py devices/<slug>/dev.yaml compile
```

## Common commit gate

Use this same gate for a clean `start` merge, a clean merge resumed by
`continue`, every clean fallback checkpoint, and an authorized conflict
resolution. Keep the merge uncommitted throughout the gate:

1. Regenerate only the source-derived outputs required by the incoming and local
   source diff. Run focused configuration, compile, host, and web checks before
   staging; record hardware separately. A blocker leaves the merge uncommitted
   and stops the run.
2. Stage only the reviewed resolution and intended generated outputs. Run
   `git diff --cached --check`, inspect the complete staged merge with
   `git diff --cached` and `git status`, and verify no unrelated path, secret,
   hosted-JavaScript decision, or unsupported-feature decision entered it.
3. Run the final full automated profiles while the complete merge is still
   staged and uncommitted. If any required automated check blocks, record the
   result, leave the merge uncommitted, and stop; do not commit a blocker.
4. Commit only after the focused checks, entire staged-diff inspection, and all
   required full automated checks pass. Record the commit and results in the
   plan, then update the strategy-specific continuation point.

## `resolve`: review, resolve, validate, commit, stop

1. Verify the persisted plan and merge state. Inspect `git status`, unmerged
   paths, `git diff --cc`, `git diff --theirs`, `git diff --ours`, and relevant
   history. Categorize each conflict and preserve device-specific and hosted-JS
   intent. Unknown shared behavior requires the approval gate above.
2. Apply the smallest approved resolution, regenerate source-derived outputs,
   run focused configuration/compile/host/web checks, and inspect the staged
   diff. Stage only the reviewed resolution and generator outputs.
3. Use the common commit gate. Record the validated merge SHA and all results,
   and stop. Do not start another merge or silently run `continue`; a resolution
   commit is an explicit continuation boundary.

## `continue`: resume, never restart

Verify the plan before every action. If the plan is waiting for shared-source
approval and that approval is now recorded, perform the one already-planned
frozen-target merge; this is not a new fetch or target. If `MERGE_HEAD` remains,
resume the uncommitted merge's regeneration and validation; unresolved paths
still require `resolve`, while a clean merge uses the common commit gate. If the
merge was committed, resume final validation and review. In `single` strategy,
stop after that target is committed. In `fallback` strategy, after a checkpoint
is committed, verify the next approved checkpoint and use the common commit gate
for it; stop at a conflict or blocker, and wait for `continue` after every
resolution commit. Never fetch, switch targets, recreate the first-parent list,
or merge an unapproved checkpoint.

## `fallback approved`: safe abort and frozen checkpoints

From the frozen first-parent list, propose only a few ordered checkpoint SHAs
(for example first, middle, and target, deduplicated). Verify the proposed list
as an ancestor chain before asking for approval: for each checkpoint, verify
`git merge-base --is-ancestor <base-sha> <checkpoint-sha>` and
`git merge-base --is-ancestor <checkpoint-sha> <target-sha>`; verify each
checkpoint is an ancestor of the next, and verify the final checkpoint is
exactly the frozen target. Record the proposed list. Require explicit user
approval naming the current attempt, authorizing the abort, and approving that
exact ordered list before starting any fallback merge. Approval of abort alone
is insufficient.

Before `git merge --abort`, compare status and staged/unstaged diffs with the
plan's pre-merge snapshot and identify which edits are merge-owned. If any
post-merge user work could be lost, or the comparison is uncertain, pause
instead of aborting. After the approved abort, record the abort and use only the
approved list; never fetch or select a new checkpoint from a moving ref.

For each approved checkpoint, run `git merge --no-ff --no-commit
<checkpoint-sha>` and use the common commit gate. Record checkpoint progress
separately from the total upstream commit count. Stop at the first conflict for
`resolve`; after any resolution commit, wait for `continue` before the next
checkpoint.

## Final review and completion

After the frozen target is integrated and all required checks pass:

1. Inspect the final upstream diff (`base..target`), the contribution diff for
   the upstream PR (`git diff <target-sha>...HEAD`, or `<target-sha>..HEAD` once
   target ancestry is verified), and the final branch diff (`starting HEAD..HEAD`).
   Also inspect the first-parent log, generated-output scope, merge parents, and
   status. Confirm no JC4827 hosted-JS decision or unsupported feature changed
   accidentally.
2. Confirm `git merge-base --is-ancestor <target-sha> HEAD`, no merge conflict
   remains, every required automated check passed, and the worktree contains no
   uncommitted resolution or generated output. An unavailable required check is
   `integrated/validation-blocked`, not complete. Hardware not run is reported
   separately and is not automatically a blocker unless hardware testing was
   explicitly made a requirement. Mark the plan complete only after required
   automated checks pass.
3. Report a PR-ready summary (purpose, upstream target, merge/checkpoint SHAs,
   generated files, separate validation results, hardware not-run evidence, and
   known risks). Do not push or create/update a PR.

Completion means the frozen target is an ancestor of `HEAD`, no conflict remains,
and every required automated validation passes. If integration is committed but
a required automated check is unavailable or fails, report
`integrated/validation-blocked` and do not mark complete. Hardware status remains
separate. Completion does not mean that every first-parent commit was merged
individually; report both counts and the exact integration checkpoints.

## Required report

Report the plan path; starting/current branch and HEAD; frozen remote/ref,
target, base, total upstream commits, completed/remaining integration
checkpoints; merge and resolution SHAs; conflict categories and approvals;
regeneration commands and outputs; distinct configuration, compile, host, web,
and hardware results; pre-existing/environment failures; final diff review;
whether the tree is clean, conflicted, staged, or committed; and that no push or
PR was performed.
