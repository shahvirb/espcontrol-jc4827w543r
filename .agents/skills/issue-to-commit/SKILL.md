---
name: issue-to-commit
description: >-
  Pick the highest-priority open GitHub issue and carry it through planning,
  implementation, validation, and review. Use when asked to work the next issue
  or take an issue from the board through implementation; stop to ask before
  creating a commit.
---

1. Find the highest-priority open issue in the repository's configured tracker; use `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` to interpret its status.
2. Read the issue, comments, related context, and worktree state; preserve existing user changes.
3. Define the outcome, acceptance criteria, dependencies, affected behavior, and validation needed; ask the user about unresolved decisions.
4. Present a concise plan, then implement the issue within its acceptance criteria.
5. Run the narrowest relevant checks, followed by broader validation when practical.
6. Review the diff against the issue, repository conventions, and regression risks; fix findings and rerun affected checks.
7. Report the changes, validation results, remaining risks, and Git status, then ask: “Are you ready for me to create the Git commit?”
8. Wait for explicit confirmation; then inspect `git status`, `git diff`, and `git log --oneline -10`, stage only the intended files, create a concise commit, and report its hash.
