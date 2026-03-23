# PRD: Auto-merge Template Updates and Warn on Conflicts

**GitHub Issue**: [#148](https://github.com/jeremysball/alfred/issues/148)  
**Status**: Draft  
**Priority**: High  
**Created**: 2026-03-22

---

## 1. Problem Statement

Alfred’s templates can drift after a restart.

When the upstream template files change, the workspace copy may already have local edits. The current sync behavior is not strong enough for that situation:
- it can leave files stale
- it can silently preserve an old version
- it does not provide a git-like conflict path when changes cannot be merged cleanly
- it does not give the WebUI a persistent, obvious warning when a conflicted context file is in play

That creates a bad failure mode: Alfred can boot, but his prompt context may be missing an important file or carrying a stale version without the user clearly knowing why.

This PRD fixes that by making template sync merge-aware, conflict-aware, and visibly unsafe when it needs to be.

---

## 2. Goals & Success Criteria

### Goals

1. Detect template changes after a full app restart and reconcile them on first successful connect.
2. Track a base snapshot for each synced template so merge behavior is effectively git-like.
3. Attempt an automatic merge before falling back to conflict markers.
4. Write standard git conflict markers when a merge fails.
5. Block conflicted files from context loading so Alfred never reads broken template text.
6. Show a persistent warning in the WebUI whenever context is loaded and conflicts exist.
7. Keep the warning available in `/context` so the issue is visible in introspection.

### Success Criteria

- On restart, Alfred tries to merge template changes instead of blindly overwriting workspace files.
- Clean merges update the workspace file and refresh the stored base snapshot.
- Conflicted files are written with standard git markers only:
  - `<<<<<<< ours`
  - `=======`
  - `>>>>>>> theirs`
- Conflicted files are excluded from prompt/context loading until resolved.
- The WebUI shows a persistent warning any time context is loaded while a conflict exists.
- The warning stays visible until the conflict is resolved.
- CLI can mirror the warning as a smaller note.
- Telegram remains deprecated and out of scope.

---

## 3. Proposed Solution

### 3.1 Track a merge base for synced templates

Keep metadata for each managed template so Alfred knows the last version that was successfully synced.

At minimum, the sync metadata should preserve:
- the file identity
- the last synced template version or hash
- the current workspace state
- whether the file is clean, merged, or conflicted

This is what makes the merge path behave like git instead of a simple copy operation.

### 3.2 Perform a 3-way merge on startup

On cold start, when the first user connection arrives, Alfred should:
1. read the current template version
2. read the workspace version
3. read the saved merge base
4. attempt a 3-way merge

If the merge succeeds, Alfred writes the merged result back to the workspace copy and updates the stored base snapshot.

If the merge fails, Alfred writes standard conflict markers and marks the file as blocked.

### 3.3 Fail closed on conflicted files

A conflicted file must not be loaded into the active context.

That means:
- no prompt assembly from the conflicted file
- no silent fallback to an older version
- no pretending the file is fine

Alfred should still boot, but the prompt context must be honest about the missing or blocked file.

### 3.4 Warn persistently in the WebUI

The WebUI should show a persistent warning whenever context is loaded and a conflicted file exists.

This warning should be obvious enough that the user cannot miss it, but it should not block the rest of the app from running.

The warning should persist until the user resolves the conflict.

### 3.5 Keep the output git-compatible and diff-friendly

The merge result must use standard git conflict markers and should not invent custom merge prose inside the file.

That keeps the output:
- familiar to users
- compatible with diff tools
- easy to copy into a real merge workflow if needed

---

## 4. Technical Implementation

### Likely file changes

```text
src/alfred/templates.py                  # merge-aware sync, conflict markers, base snapshot tracking
src/alfred/context.py                    # block conflicted files from context loading
src/alfred/context_display.py            # expose sync/conflict state in /context
src/alfred/alfred.py                     # trigger sync checks from runtime startup if needed
src/alfred/cli/main.py                   # first-connect / startup wiring and warning text
src/alfred/interfaces/webui/server.py    # persistent WebUI warning and context payload changes
src/alfred/interfaces/webui/static/js/main.js
src/alfred/interfaces/webui/static/css/base.css

tests/test_templates.py
tests/test_context_integration.py
tests/test_system_md_integration.py
tests/webui/test_*.py
```

### Implementation notes

- The sync flow should be safe to run more than once.
- The merge base should survive restarts so Alfred can reason about later changes.
- The context loader should have a single source of truth for whether a file is blocked.
- The WebUI warning should use the same sync state rather than re-deriving it in the browser.
- If a file is conflicted, the app should continue to run, but the affected context should fail closed.

---

## 5. Milestones

### Milestone 1: Define the sync metadata contract
Lock down how Alfred records the last synced base, current workspace status, and conflict state.

Validation: the metadata format is documented and stable enough to drive merge behavior.

### Milestone 2: Capture base snapshots for synced templates
Store enough history to support a real 3-way merge on the next restart.

Validation: Alfred can recover the last synced version for each managed template.

### Milestone 3: Implement git-style auto-merge on restart
Attempt a clean merge when templates change and workspace files already exist.

Validation: unchanged or trivially changed files merge automatically and refresh their sync state.

### Milestone 4: Write standard conflict markers on merge failure
When a merge cannot be resolved automatically, write standard git markers into the file.

Validation: conflicted files are easy to inspect with normal diff tools.

### Milestone 5: Block conflicted files from context loading
Prevent conflicted templates from entering prompt assembly.

Validation: Alfred loads without the conflicted file, and the missing state is explicit.

### Milestone 6: Surface persistent warnings in the WebUI and `/context`
Make the conflict state obvious whenever context is loaded while a conflict exists.

Validation: the warning persists until the user resolves the file.

### Milestone 7: Add regression tests for clean merge, conflict, and fail-closed loading
Cover the merge path and the warning path with realistic tests.

Validation: tests prove the app merges, blocks, and warns correctly.

### Milestone 8: Update documentation and operator guidance
Explain how template sync works, what the markers mean, and how to resolve conflicts.

Validation: docs describe the workflow without requiring source code spelunking.

---

## 6. Validation Strategy

### Required checks
- `uv run pytest tests/test_templates.py tests/test_context_integration.py tests/test_system_md_integration.py -q`
- `uv run pytest tests/webui/test_integration.py tests/webui/test_server.py tests/webui/test_websocket.py -q`
- `uv run pytest tests/webui -q`
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- `uv run pytest`
- `uv run alfred webui`

### Runtime verification
- Start from a cold app state
- Change a template file
- Confirm the first connect after restart attempts a merge
- Confirm conflict files are blocked from context loading
- Confirm the WebUI shows a persistent warning while the conflict exists

### What success looks like
- Alfred never silently hides template drift.
- Clean updates merge automatically.
- Conflicts are obvious, git-like, and diff-friendly.
- Broken template text never enters the active context.
- The WebUI makes the problem hard to miss.

---

## 7. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Merge logic corrupts a template | High | Medium | keep the merge algorithm conservative and fail closed on ambiguity |
| Conflict markers leak into prompt context | High | Low | block conflicted files from loading entirely |
| Sync metadata gets out of date | Medium | Medium | update the stored base only after successful merge or confirmed clean sync |
| Persistent warnings become noisy | Medium | Medium | keep the warning scoped to actual conflicts and clear it automatically when fixed |
| Startup becomes harder to reason about | Medium | Medium | keep the merge step isolated and idempotent |
| The app becomes dependent on a particular merge implementation | Medium | Low | define the output contract in terms of git-compatible markers, not a single library |

---

## 8. Non-Goals

- a visual merge editor
- diff3 markers or custom merge syntax
- automatic conflict resolution beyond standard merge attempts
- Telegram-specific warning surfaces
- forcing the app to stop when a template conflicts
- replacing the existing config update command with a full VCS client

---

## 9. Future Direction

This merge-aware sync path could later be reused for other synchronized prompt assets, but the first job is to make template drift visible and safe.

Potential follow-ups:
- richer conflict inspection in `/context`
- selective merge support for additional prompt fragments
- better operator tools for resolving conflicts in-place

Any later expansion should keep the same fail-closed behavior.

---

## 10. Resolved Design Decisions

1. **Use standard git conflict markers.**
2. **Attempt automatic merge before conflict markers.**
3. **Block conflicted files from context loading.**
4. **Keep the warning persistent in the WebUI until the conflict is resolved.**
5. **Telegram is deprecated and out of scope.**
6. **The feature must be diff-friendly and not invent custom conflict syntax.**

---

## 11. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-22 | Track a base snapshot for synced templates | A real merge needs a merge base, not just a two-way compare |
| 2026-03-22 | Use git-style conflict markers | The output should be familiar and compatible with diff tooling |
| 2026-03-22 | Fail closed on conflicted files | Broken template text must not enter the active context |
| 2026-03-22 | Show a persistent WebUI warning while conflicts exist | The problem should be visible every time context is loaded |
| 2026-03-22 | Keep the app running even if a template conflicts | Alfred should remain usable while the operator resolves the issue |
| 2026-03-23 | Keep the sync store lazy-loaded behind `TemplateManager.get_base_snapshot()` | Avoid eager cache side effects on manager construction while still recovering snapshots after restart |
| 2026-03-23 | Treat sync-store writes as best-effort during template updates | A cache write failure should not roll back a successful workspace update |
| 2026-03-23 | Fast-forward clean template updates when the workspace still matches the saved base snapshot | Content identity is the authoritative signal for a clean fast-forward, even when mtimes are stale |
