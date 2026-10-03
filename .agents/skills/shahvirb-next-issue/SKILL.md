---
name: shahvirb-next-issue
description: Select the next relevant device-integration issue and produce a solution plan after user approval.
disable-model-invocation: true
---

# Next Issue

1. Read `AGENTS.md`, `docs/agents/issue-tracker.md`, and the triage labels. Use `gh` to review the repository's open issues, comments, labels, and dependencies, then choose the next issue logically.
2. Confirm the issue fits the device-integration goal in `AGENTS.md`. If it does not, report that and stop.
3. Search open and closed issues in `jtenniswood/espcontrol` for a semantically equivalent issue. Report whether an upstream equivalent exists, the benefit of addressing the issue, the consequence of leaving it unresolved, and a high-level recommendation.
4. If an upstream equivalent exists, stop and ask whether the user wants to continue. Otherwise, also wait for the user's approval before planning.
5. After approval, produce only a high-level solution plan covering the outcome, affected areas, approach, and validation. Do not implement, edit issues, commit, or create a pull request.
