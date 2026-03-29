# PRD: Selective Tool Outcomes and Context Viewer Fixes

**GitHub Issue**: [#165](https://github.com/jeremysball/alfred/issues/165)  
**Status**: In Progress  
**Priority**: High  
**Created**: 2026-03-28  
**Author**: Agent

---

## 1. Problem Statement

Alfred currently treats tool-call history as context in a way that is too noisy and too literal.

Four related problems show up together:

1. **Raw tool calls pollute context**
   - Current context assembly can inject a separate "recent tool calls" section with arguments and output from prior tool usage.
   - This wastes tokens on mechanics instead of meaning.
   - Retrieval quality degrades when the model sees tool syntax, argument blobs, and repeated execution details instead of the actual user/assistant conversation.

2. **The context viewer is not trustworthy**
   - The Web UI `/context` component has broken prompt-section toggle behavior.
   - Section identifiers do not line up cleanly between frontend and backend.
   - The viewer misrepresents prompt composition by omitting sections such as `SYSTEM.md` and by reporting only a tiny slice of session history as though it were the real context.

3. **Session history visibility is too small and too misleading**
   - `/context` currently shows only a handful of session messages.
   - The visible count is effectively treated as the total count.
   - Users cannot tell what is actually in prompt context versus what is simply hidden by the viewer.

4. **Conflicted managed templates are hidden too quietly**
   - When a managed template is conflicted, the context surface only hints at a blocked file.
   - The user cannot immediately tell which template is conflicted or why it is absent from prompt context.
   - The context menu should call this out explicitly so the missing context is explainable.

The result is a context system that is noisy for the model, confusing for the user, and incomplete about template conflicts.

---

## 2. Goals

1. Replace raw tool-call context with **selective derived tool outcomes**.
2. Preserve enough execution history for the model to understand what happened without replaying raw tool-call payloads.
3. Make `/context` report prompt composition and session history truthfully.
4. Surface conflicted managed templates explicitly in the context menu and Web UI.
5. Use session messages as the final spillover layer after higher-priority context types are filled.
6. Fix the Web UI context component so prompt section toggles actually work.
7. Verify the Web UI context surface through real browser behavior.

---

## 3. Non-Goals

- Removing tool-call persistence from session transcripts or resumed-session UI.
- Redesigning the entire memory system.
- Reworking the full Web UI layout beyond what is needed to make the context component functional and truthful.
- Reworking the full context-budget architecture beyond the spillover policy defined here.
- Preserving backward-compatible raw tool-call context behavior.

---

## 4. Proposed Solution

### 4.1 Replace raw tool-call context with selective derived outcomes

Do not inject raw tool-call records into retrieved model context.

Instead, represent prior tool activity as compact, human-readable outcomes when that history is actually useful.

Recommended default policy:

- **`bash`**
  - include command
  - include exit code
  - include short trimmed output
  - example: `bash: rg "ContextViewer" src exited 0 — found 6 matches`

- **`read`**
  - include project-relative path
  - example: `read: src/alfred/context.py`

- **`edit`**
  - include project-relative path and outcome
  - example: `edit: updated src/alfred/context.py`

- **`write`**
  - include project-relative path and outcome
  - example: `write: created tests/webui/test_context_viewer.py`

- **other tools**
  - include only a minimal outcome when the result materially affects the conversation
  - avoid raw argument dumps and large output blobs

This keeps the model aware of what happened while deleting low-value mechanics.

### 4.2 Remove the standalone recent tool-calls context block

The assembled prompt should not contain a separate block of raw recent tool calls.

If tool history is needed, it should appear as compact derived outcomes folded into the recent session context rather than as a second transcript of arguments and output.

### 4.3 Make `/context` truthful about what it shows

The context display should distinguish between:

- **total session messages available**
- **messages currently shown in the viewer**
- **messages actually included in prompt context** when that differs
- **blocked or conflicted managed templates** that are no longer active

This PRD adopts **preview + truth** behavior:

- the viewer may show a bounded preview for readability
- the counts must clearly report reality
- the UI must stop implying that a small visible slice is the full context
- blocked/conflicted managed files must be called out explicitly, not only as a generic warning

### 4.4 Surface template conflicts explicitly in `/context`

Managed template conflicts should be visible in both the TUI and Web UI context surfaces.

Requirements:
- show conflicted file names explicitly
- explain that the files are blocked because the managed template is conflicted
- keep conflict details separate from unrelated disabled sections

### 4.5 Make session history the final spillover layer

Session messages should be added after system prompt sections, memories, and other derived context.

Requirements:
- fill the remaining budget with session messages after higher-priority context types are placed
- prefer the newest session messages first when budget is limited
- preserve chronological order within the included slice
- keep the viewer accurate about how many messages were included versus how many exist total

### 4.6 Fix prompt section toggles end to end

The Web UI context component and backend command handling must use one stable section identity scheme.

Requirements:
- frontend toggle IDs and backend section names match exactly
- enabled and disabled state render correctly
- toggling a section updates the backend
- the refreshed context view reflects the new state immediately

### 4.7 Show real prompt sections

The system prompt breakdown in `/context` should reflect the prompt that Alfred actually builds.

At minimum, that means the viewer must correctly account for managed sections such as:
- `SYSTEM.md`
- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md` when present and active

### 4.8 Verify through browser-level behavior

Because the bug is user-visible and centered in a Web Component, acceptance must include browser behavior tests.

At minimum, browser verification should prove:
- `/context` renders structured context data
- prompt section toggles work
- refreshed state stays in sync with backend data
- the session-history section communicates preview vs prompt-included vs total counts clearly, using a compact badge when the values match and the full triplet when they differ
- the browser validates the viewer through the real `/context` command flow, not a direct DOM-only shortcut

---

## 5. User Experience Requirements

### 5.1 Model-facing context quality

When Alfred has recently used tools, the next turn should see compact evidence of what happened, not raw execution payloads.

Desired effect:
- the model understands that a file was read, edited, or written
- the model understands whether a shell command succeeded or failed
- the model does not waste context on JSON-like tool argument blobs or long output logs

### 5.2 `/context` viewer clarity

A user opening `/context` in the Web UI should be able to answer these questions immediately:

- Which prompt files are active?
- Which prompt files are disabled?
- Which prompt files are conflicted?
- How many prompt sections are active versus disabled?
- How many session messages exist?
- How many session messages are included in prompt context?
- How many are being previewed here?
- Is tool activity being represented compactly or as raw output?

The viewer should label counts explicitly:

- system prompt badge: `N active / M disabled`
- session history badge: `N messages` when preview, prompt-included, and total are the same; otherwise `X displayed / Y included / Z total messages`

### 5.3 Session preview behavior

The viewer does not need to dump the entire session into one enormous panel by default, but it must never confuse a preview for the total dataset. When session history is also serving as spillover context, the preview must still make clear which messages are actually in the prompt.

---

## 6. Technical Requirements

### 6.1 Context assembly

- Delete raw tool-call prompt injection from `ContextBuilder`.
- Replace it with derived outcome formatting.
- Build prompt context in priority order: system prompt, memories, derived tool outcomes, then session messages.
- Session messages should consume the remaining token budget after higher-priority context types are placed.
- When budget is tight, pack the newest session messages first and preserve their order within the included slice.
- Keep the formatting small and deterministic.
- Use project-relative paths in context text.
- Respect existing context budget behavior.

### 6.2 Session/context display

- `/context` should include accurate counts for session history, clearly distinguishing displayed preview items, prompt-included items, and the total available messages.
- The shared payload should expose `displayed`, `included`, and `total` session-history counts so the browser can render them without guessing.
- `/context` should explicitly surface conflicted managed templates or blocked context files with the reason they are blocked.
- `/context` should include accurate counts for displayed tool outcomes if surfaced.
- `/context` should report system prompt sections from the same source of truth used by prompt assembly.
- The Web UI should render system prompt counts as `N active / M disabled` and session history counts as `N messages` when the counts are identical, expanding to preview / included / total only when those values differ.

### 6.3 Web UI contract

- frontend payload handling must match backend field names exactly
- section toggle identifiers must map cleanly to backend section toggling
- browser events from the context viewer must produce working server commands

### 6.4 Storage and transcript policy

- keep raw tool calls persisted in session records for transcript fidelity and resumed-session rendering
- do not treat persisted raw tool calls as the default retrieval/context representation

---

## 7. Success Criteria

- [x] Assembled prompt no longer includes a raw `RECENT TOOL CALLS` block.
- [x] Prior tool activity appears in context only as selective derived outcomes.
- [x] `bash` outcomes include command, exit code, and trimmed output.
- [x] `read`, `edit`, and `write` outcomes include project-relative path and compact status.
- [x] `/context` reports real prompt sections, including `SYSTEM.md` when active.
- [x] `/context` explicitly surfaces conflicted managed templates and blocked context files.
- [x] Session messages are the final spillover layer and consume the remaining context budget.
- [x] `/context` distinguishes displayed preview messages from prompt-included and total session messages.
- [x] Web UI prompt section toggles work end to end.
- [ ] Browser-level regression coverage proves the context component is functional.
- [x] The implementation passes the relevant Python validation workflow.

---

## 8. Milestones

### Milestone 1: Define and enforce selective tool-outcome context
Replace raw tool-call context injection with compact derived outcome rendering, remove the standalone raw tool-call block from assembled context, and make session history the final spillover layer that consumes remaining budget.

Validation: context assembly tests prove the prompt contains derived outcomes instead of raw tool-call payloads, and that session messages are appended last.

### Milestone 2: Make session/context reporting truthful and conflict-aware
Update shared context-display data so system prompt sections, session-history counts, preview semantics, and conflicted managed templates reflect reality rather than a tiny hard-coded slice.

Validation: context-display tests prove totals, displayed counts, prompt-included counts, and conflict warnings are distinct and accurate.

### Milestone 3: Fix Web UI context-section toggles
Unify frontend/backend section identifiers and repair toggle behavior so enabling and disabling prompt sections works consistently in the Web UI.

Validation: WebSocket and component behavior tests prove toggles send the right commands and render the returned state.

### Milestone 4: Make the Web UI context component functional and clear
Update the context viewer so prompt sections, conflicted template warnings, session history, and tool outcome surfaces render clearly and truthfully.

Validation: browser behavior verifies `/context` is usable and understandable without inspecting server logs.

### Milestone 5: Regression coverage and verification
Add or update regression tests for context assembly, shared context-display data, WebSocket `/context` behavior, and browser-level interaction.

Validation: relevant Python workflow passes, including browser-facing tests needed for this change.

Progress note:
- Phases 1-3 are complete: derived tool outcomes, session spillover ordering, truthful shared `/context` data, explicit conflict surfacing, and stable toggle ids are in place.
- Remaining work is in Phase 4: the browser context viewer still needs a browser toggle round-trip regression.
- Phase 5 is partially complete: Python and JS validation pass, and browser regression coverage exists for conflict surfacing, truthful counts, and compact tool-outcome presentation, but the browser toggle-round-trip regression still needs to land.

---

## 9. Likely File Changes

```text
src/alfred/context.py
src/alfred/context_display.py
src/alfred/session.py
src/alfred/alfred.py
src/alfred/interfaces/webui/server.py
src/alfred/interfaces/webui/static/js/components/context-viewer.js
src/alfred/interfaces/webui/static/js/main.js

tests/test_context_command.py
tests/test_context_display.py
tests/test_context_integration.py
tests/webui/test_server_parity.py
tests/webui/test_websocket.py
tests/webui/test_context_warning_browser.py
# plus new or updated browser regression tests as needed
```

---

## 10. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Removing raw tool-call context hides useful execution state | Medium | keep compact derived outcomes with tool-specific rules, especially for `bash` |
| The viewer becomes truthful but too verbose | Medium | use preview + truth: bounded lists with explicit total counts |
| Frontend and backend toggle naming drift again | Medium | define one stable section-identity mapping and test it through the public interface |
| Browser tests remain flaky | Medium | keep browser checks narrowly focused on `/context` rendering and interaction |
| Existing tests encode the old misleading behavior | Low | update tests to assert truthful counts and the new derived-outcome contract |

---

## 11. Validation Strategy

This is a Python-led change with browser-visible Web UI impact.

Required validation:

```bash
uv run ruff check src/
uv run mypy --strict src/
uv run pytest -m "not slow"
```

Additional required verification for this PRD:
- targeted WebSocket `/context` regression tests
- targeted browser-level verification for the Web UI context component

---

## 12. Related PRDs

- PRD #101: Tool Call Persistence and Context Visibility
- PRD #102: Unified Memory System
- PRD #139: Web UI Test Fixture Realism
- PRD #155: Interleaved Tool Calls and Thinking Blocks
- PRD #164: Repo-wide ESM Migration for JavaScript

---

## 13. Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-28 | Do not inject raw tool calls into retrieved context | Raw payloads are noisy and reduce context quality |
| 2026-03-28 | Use derived tool outcomes instead | The model still needs compact awareness of what happened |
| 2026-03-28 | `bash` gets the richest summary: command + exit code + trimmed output | Shell execution is the least obvious tool outcome without extra context |
| 2026-03-28 | Use project-relative paths in tool outcomes | Paths should stay specific without hardcoded machine-specific absolutes |
| 2026-03-28 | `/context` uses preview + prompt-included + total counts for session history | The viewer should stay readable without lying about the prompt slice or totals |
| 2026-03-28 | Render system prompt counts as `N active / M disabled` | A single compact badge makes active and disabled sections obvious |
| 2026-03-28 | Render session history as `N messages` when counts are equal, otherwise `X displayed / Y included / Z total messages` | Keep the default browser view compact while exposing the full truth when the counts diverge |
| 2026-03-28 | Expose session-history `displayed`, `included`, and `total` counts in the shared payload | The browser should not infer prompt inclusion from preview length alone |
| 2026-03-28 | Add `session_history.included` as a first-class shared payload field | The browser needs the prompt-included count as explicit data rather than guessing from preview length |
| 2026-03-28 | Surface conflicted managed templates explicitly in `/context` | Generic blocked warnings are too vague for missing managed files |
| 2026-03-28 | Session history is the final spillover layer | Remaining context budget should be spent on conversation history after higher-priority layers |
| 2026-03-28 | Browser verification is required | The bug is user-visible and centered in the Web UI context component |
| 2026-03-28 | Use the real `/context` command flow for browser truthfulness tests | The browser should validate the actual WebSocket path users rely on |
