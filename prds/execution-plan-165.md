# Execution Plan: PRD #165 - Selective Tool Outcomes and Context Viewer Fixes

## Overview
Implement compact derived tool outcomes in prompt context, make `/context` truthful about preview vs prompt-included vs total data, surface conflicted managed templates, treat session messages as the spillover layer after higher-priority context types, unify section IDs across backend and Web UI, and verify the browser/TUI surfaces with regression tests.

---

## Phase 1: Replace raw tool-call context with derived outcomes

### Shared tool-outcome formatter

- [x] Test: `test_build_context_emits_compact_derived_tool_outcomes()` in `tests/test_context_observability.py` — verify `bash` summaries contain command + exit status + trimmed output, `read`/`edit`/`write` summaries contain project-relative paths, and `## RECENT TOOL CALLS` is absent.
- [x] Implement: extract a shared selective-outcome formatter, remove raw tool-call prompt injection from `src/alfred/context.py`, and fold the summaries into the session-history portion of the prompt.
- [x] Run: `uv run pytest tests/test_context_observability.py -v`

### Budget and truncation

- [x] Test: `test_build_context_trims_derived_tool_outcomes_when_budget_is_tight()` in `tests/test_context_observability.py` — verify long tool output is clipped and context assembly still respects `memory_budget`.
- [x] Implement: keep the new formatter deterministic and bounded, and remove the old raw-output code path.
- [x] Run: `uv run pytest tests/test_context_observability.py -v`

### Session spillover ordering

- [x] Test: `test_build_context_fills_remaining_budget_with_session_messages()` in `tests/test_context_observability.py` — verify session messages are appended last and consume the remaining budget after system prompt sections, memories, and derived tool outcomes.
- [x] Implement: pack the newest session messages into the leftover context budget, preserve order within the included slice, and keep the prompt deterministic.
- [x] Run: `uv run pytest tests/test_context_observability.py -v`

---

## Phase 2: Make shared `/context` data truthful

### Session preview vs total

- [x] Test: `test_get_context_display_reports_session_history_preview_and_total()` in `tests/test_context_display.py` — verify the payload distinguishes displayed preview messages from the total available session history.
- [x] Implement: add `displayed` and `total` counts to `session_history` in `src/alfred/context_display.py`, keep the preview bounded, and stop treating preview length as the full count.
- [x] Run: `uv run pytest tests/test_context_display.py -v`

### Managed prompt sections

- [x] Test: `test_get_context_display_includes_system_md_and_matches_prompt_order()` in `tests/test_context_display.py` — verify `SYSTEM.md` is included and the section order matches prompt assembly (`SYSTEM`, `AGENTS`, `TOOLS`, `SOUL`, `USER`).
- [x] Implement: report the managed prompt files from the same source of truth as `ContextLoader._build_system_prompt`, and expose stable section identifiers plus display labels.
- [x] Run: `uv run pytest tests/test_context_display.py -v`

### Conflict surfacing

- [x] Test: `test_get_context_display_reports_conflicted_context_files_and_omits_blocked_sections()` in `tests/test_context_display.py` — verify conflicted managed templates are called out explicitly instead of being hidden behind a generic blocked-file warning.
- [x] Implement: add explicit conflict details and reasons to the shared context-display payload so TUI/Web UI surfaces can render them directly.
- [x] Run: `uv run pytest tests/test_context_display.py -v`

### Compact tool activity summary

- [x] Test: `test_get_context_display_reports_compact_tool_outcomes()` in `tests/test_context_display.py` — verify tool activity is summarized compactly, with preview-vs-total counts and no raw argument/output blobs.
- [x] Implement: replace raw tool-call items in the context display with compact derived outcomes from the shared formatter.
- [x] Run: `uv run pytest tests/test_context_display.py -v`

### TUI `/context` output contract

- [x] Test: `test_show_context_command_reports_preview_counts_and_compact_tool_outcomes()` in `tests/test_context_command.py` — verify the TUI output uses the new labels/counts and compact summaries.
- [x] Implement: update `src/alfred/interfaces/pypitui/commands/show_context.py` to read the new payload contract and print `SYSTEM.md` labels, preview-vs-total counts, and tool outcomes.
- [x] Run: `uv run pytest tests/test_context_command.py -v`

---

## Phase 3: Unify section identifiers end to end

### Stable toggle IDs

- [x] Test: `test_command_context_toggle_uses_section_ids()` in `tests/webui/test_websocket.py` — verify `/context toggle` uses stable ids (`SYSTEM`, `AGENTS`, `TOOLS`, `SOUL`, `USER`) rather than display labels.
- [x] Implement: update `src/alfred/interfaces/webui/static/js/components/context-viewer.js` to dispatch stable ids and have `src/alfred/interfaces/webui/static/js/main.js` send the matching command.
- [x] Run: `uv run pytest tests/webui/test_websocket.py -v -k context`

### Refresh state sync

- [x] Test: `test_context_info_refresh_keeps_disabled_sections_in_sync()` in `tests/webui/test_server_parity.py` — verify the refreshed `/context` payload reflects the toggled state without stale labels or mismatched identifiers.
- [x] Implement: keep the `disabled_sections` payload and section labels aligned, and remove the legacy `disabledSections` frontend mismatch.
- [x] Run: `uv run pytest tests/webui/test_server_parity.py -v -k context`

---

## Phase 4: Make the Web UI context viewer clear and functional

### Truthful section rendering

- [x] Test: `test_browser_context_viewer_renders_truthful_section_counts()` in `tests/webui/test_context_warning_browser.py` — verify the browser shows active vs disabled vs conflicted prompt sections, the system prompt section list, and session history as `N messages` when counts match or `X displayed / Y included / Z total messages` when they differ.
- [x] Implement: update `src/alfred/context_display.py` and `src/alfred/interfaces/webui/static/js/components/context-viewer.js` to expose and render `session_history.displayed`, `session_history.included`, and `session_history.total` with the new badge labels.
- [x] Run: `uv run pytest tests/webui/test_context_warning_browser.py -v -m slow`

### Compact tool activity display

- [x] Test: `test_browser_context_viewer_shows_compact_tool_outcomes()` in `tests/webui/test_context_warning_browser.py` — verify the browser does not render raw argument blobs or long output dumps for tool activity.
- [x] Implement: render the derived tool-outcome summaries in the viewer and drop the raw tool-call panel.
- [x] Run: `uv run pytest tests/webui/test_context_warning_browser.py -v -m slow`

### Toggle round trip

- [x] Test: `test_browser_context_viewer_toggles_sections_and_refreshes()` in `tests/webui/test_context_warning_browser.py` — verify clicking a checkbox sends the correct command and the refreshed payload updates the UI state.
- [x] Implement: keep the context-toggle refresh path intact through the viewer and websocket command handler.
- [x] Run: `uv run pytest tests/webui/test_context_warning_browser.py -v -m slow`

---

## Phase 5: Regression coverage and final verification

### Update existing contract tests

- [x] Test: update the existing `/context` assertions in `tests/webui/test_server_parity.py`, `tests/webui/test_websocket.py`, and `tests/test_context_command.py` to cover the new payload shape, stable ids, truthful counts, conflict warnings, and spillover ordering.
- [x] Implement: remove legacy assumptions about raw tool calls, `count`-only session history, and `.md`-suffixed toggle ids.
- [x] Run: `uv run pytest tests/webui/test_server_parity.py tests/webui/test_websocket.py tests/test_context_command.py -v`

### Full validation

- [x] Run: `uv run ruff check src/ && uv run mypy --strict src/ && uv run pytest -m "not slow"`
- [x] Run: `npm run js:check`

---

## Files to Modify

1. `src/alfred/context.py`
2. `src/alfred/context_display.py`
3. `src/alfred/context_outcomes.py` - shared selective tool-outcome formatter if extracted
4. `src/alfred/interfaces/pypitui/commands/show_context.py`
5. `src/alfred/interfaces/webui/static/js/components/context-viewer.js`
6. `src/alfred/interfaces/webui/static/js/main.js`
7. `tests/test_context_observability.py`
8. `tests/test_context_display.py`
9. `tests/test_context_command.py`
10. `tests/webui/test_server_parity.py`
11. `tests/webui/test_websocket.py`
12. `tests/webui/test_context_warning_browser.py`

## Commit Strategy

- One checkbox = one atomic commit.
- Prefer deleting the raw path rather than preserving parallel behavior.
