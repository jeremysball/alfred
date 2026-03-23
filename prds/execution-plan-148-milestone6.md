# Execution Plan: PRD #148 - Milestone 6: Surface Persistent Warnings in the WebUI and `/context`

## Overview
Make blocked managed templates visible wherever Alfred shows context, using the shared context-display payload as the single source of truth. This phase should reuse the existing system-message surfaces in the TUI and WebUI instead of inventing a new banner system.

---

## Phase 6: Make blocked context files obvious to operators

### Component: Shared warning data and `/context` command output

- [x] **Test**: `test_show_context_command_reports_blocked_context_warning_and_omits_blocked_sections()` - verify the shared context display omits blocked template sections, reports blocked file names, and the `/context` TUI command renders a warning block before the normal context breakdown
- [x] **Implement**: extend `get_context_display()` to return `blocked_context_files` plus a human-readable `warnings` list, filter blocked files out of the system prompt section summary, and prepend the warning in `ShowContextCommand.execute()`
- [x] **Run**: `uv run pytest tests/test_context_command.py::test_show_context_command_reports_blocked_context_warning_and_omits_blocked_sections -v`

### Component: WebUI warning rendering through the shared context path

- [x] **Test**: `test_browser_context_warning_renders_persistent_system_message()` - verify the WebUI `/context` path renders the blocked-context warning as a persistent system message in the chat transcript
- [x] **Implement**: pass the shared `warnings` / `blocked_context_files` payload through `_build_context_payload()` and render the warning block in `handleContextInfo()` as a system message before the normal context sections
- [x] **Run**: `uv run pytest tests/webui/test_context_warning_browser.py -v`

---

## Progress Summary

Milestone 6 is complete.
Continue with Milestone 7: Add regression tests for clean merge, conflict, and fail-closed loading in `prds/148-template-sync-merge-conflicts.md`.

## Files to Modify

1. `src/alfred/context_display.py` — expose blocked context files and warnings from the shared context data
2. `src/alfred/interfaces/pypitui/commands/show_context.py` — render the warning block in the TUI `/context` output
3. `src/alfred/interfaces/webui/server.py` — include blocked-context warning data in the websocket payload
4. `src/alfred/interfaces/webui/static/js/main.js` — render the warning block in the WebUI system message
5. `tests/test_context_command.py` or `tests/test_context_display.py` — coverage for shared warning data and TUI rendering
6. `tests/webui/test_context_warning_browser.py` — browser-level regression coverage for the WebUI warning path

## Commit Strategy

Each completed checkbox should be one atomic commit:
- `test(context): cover blocked-context warning output`
- `feat(context): surface blocked template warnings in /context`
- `test(webui): cover blocked-context warning rendering`
- `feat(webui): show persistent blocked template warnings`

## Exit Criteria for Milestone 6

- `/context` shows blocked templates explicitly and omits them from the active prompt summary
- The WebUI shows the same warning through the shared context path
- The warning persists in the chat transcript until the conflict is resolved
- Milestone 7 can focus on regression coverage and edge cases
