# Execution Plan: PRD #183 - Milestone 6A (Web UI only): Inspect v2 value ledger entries via `/context`

## Overview
Ship the first **Web UI-only** inspection surface for PRD #183’s v2 learning artifacts by extending the existing `/context` → `context.info` payload and rendering the full v2 **value ledger** (support + relational) inside the Web UI `context-viewer`.

This slice is intentionally **not a TUI feature**: no new TUI commands, no CLI rendering changes. The Web UI will surface the data using the existing `/context` command path.

### What this slice covers
- v2 **SupportValueLedgerEntry** inspection (all statuses: `shadow`, `active_auto`, `confirmed`, `rejected`, `retired`)
- v2 **SupportLedgerUpdateEvent** inspection (recent events; value-entity focused)
- Web UI rendering inside the existing **Support State** section of `context-viewer`

### What this slice explicitly defers
- `/support values` TUI command and rendering
- `/support cases`, `/support trace`, `/support patterns`
- pattern inference display
- runtime rewiring to load v2 values (this is inspection only)


## Current Repo Constraints
- The Web UI receives `/context` via WebSocket (`command.execute` → `context.info`) and renders it using `src/alfred/interfaces/webui/static/js/components/context-viewer.js`.
- `src/alfred/context_display.py` builds `support_state` by calling `SupportReflectionRuntime.build_inspection_snapshot()`.
- `SupportReflectionRuntime` currently surfaces patterns + v1 update events, but **does not** include v2 value-ledger entries nor v2 ledger-update events.
- SQLite persistence already exists for:
  - `SupportValueLedgerEntry` (`support_value_ledger_entries`)
  - `SupportLedgerUpdateEvent` (`support_ledger_update_events`)
- This milestone must avoid expanding scope into TUI command plumbing.


## Success Signal (observable)
In the Web UI:
1. User enters `/context`.
2. The resulting `context.info.payload.support_state.learned_state` includes:
   - `value_ledger_entries` (bounded list, deterministic order)
   - `value_ledger_summary` (counts by status + totals)
   - `recent_ledger_update_events` (bounded list)
3. `context-viewer` renders a **Value Ledger** card under **Support State**, listing ledger entries with:
   - registry, dimension, scope, value, status, confidence, evidence_count, contradiction_count
   - (optional) expandable “why” text
4. The view is deterministic and does not require any TUI changes.


## Validation Workflow
**Workflow:** Python + JavaScript

Python checks:
```bash
uv run ruff check src/ tests/test_support_reflection.py tests/webui/test_server_parity.py
uv run mypy --strict src/
uv run pytest \
  tests/test_support_reflection.py \
  tests/webui/test_server_parity.py \
  -v
```

JavaScript checks:
```bash
npm run js:check
```

Browser verification (targeted, slow):
```bash
uv run pytest tests/webui/test_support_value_ledger_browser.py -v
```


---

## Phase 1: Add v2 value-ledger inspection data to the `/context` payload

### Extend support-inspection snapshot to include v2 values + v2 ledger events

- [x] **Test (Python):** extend `tests/test_support_reflection.py` with `test_support_inspection_snapshot_includes_v2_value_ledger_entries_and_recent_ledger_events()`.
  - Use the existing `FakeReflectionStore` pattern.
  - Provide fake v2 `SupportValueLedgerEntry` rows spanning multiple statuses.
  - Provide fake v2 `SupportLedgerUpdateEvent` rows.
  - Assert `SupportReflectionRuntime.build_inspection_snapshot()` returns them in deterministic order and with correct counts.

- [x] **Implement (Python):** extend `src/alfred/support_reflection.py`:
  - extend `LearnedState` with:
    - `value_ledger_entries: tuple[SupportValueLedgerEntrySummary, ...]` (summary DTO, not the raw DB record)
    - `value_ledger_summary: {total, counts_by_status, counts_by_registry}` (exact shape defined in test)
    - `recent_ledger_update_events: tuple[LedgerUpdateEventSummary, ...]`
  - extend `SupportReflectionStore` protocol to support loading:
    - `list_support_value_ledger_entries(...)` (bounded)
    - `list_support_ledger_update_events(...)` (bounded)
  - wire `SupportReflectionRuntime.build_inspection_snapshot()` to call these store methods and populate the new fields.

- [x] **Run:** `uv run pytest tests/test_support_reflection.py::test_support_inspection_snapshot_includes_v2_value_ledger_entries_and_recent_ledger_events -v`

### Ensure `/context` display forwards the new fields

- [x] **Test (Python):** extend `tests/test_context_display.py` (or add a focused new test) to assert that `get_context_display()`’s `support_state` payload includes the new learned-state fields when the reflection runtime provides them.
  - Keep this as a narrow “serialization contract” test (no DB required).

- [x] **Implement (Python):** update `src/alfred/context_display.py` to serialize the new v2 ledger summary fields into the `support_state.learned_state` dict.


---

## Phase 2: Render the value ledger in the Web UI (no TUI changes)

### Add DOM rendering for ledger entries

- [ ] **Test (browser / Playwright, slow):** add `tests/webui/test_support_value_ledger_browser.py`.
  - Start the Web UI server with `create_app(FakeAlfred())`.
  - Patch `alfred.context_display.get_context_display` to return a `context_data` payload that includes:
    - `support_state.learned_state.value_ledger_entries`
    - `support_state.learned_state.value_ledger_summary`
    - `support_state.learned_state.recent_ledger_update_events`
  - In the browser:
    - send `/context`
    - assert the page renders a “Value Ledger” card and shows at least one expected ledger entry (registry + dimension + value + status).

- [ ] **Implement (JavaScript):** update `src/alfred/interfaces/webui/static/js/components/context-viewer.js`
  - Extend `_renderSupportState()` to include a new card, e.g. “Value Ledger”.
  - Render each entry with status badge and confidence.
  - Keep deterministic ordering as provided by the payload.
  - Keep UI minimal: no fancy filtering in 6A unless required by test.

- [ ] **Run:**
  - `npm run js:check`
  - `uv run pytest tests/webui/test_support_value_ledger_browser.py -v`


---

## Phase 3: WebSocket protocol docs alignment

- [ ] **Docs:** update `docs/websocket-protocol.md` `context.info` payload description to mention the new `support_state.learned_state.value_ledger_entries` and `recent_ledger_update_events` fields.


---

## Final phase verification

- [ ] Run: `uv run ruff check src/ tests/test_support_reflection.py tests/webui/test_server_parity.py`
- [ ] Run: `uv run mypy --strict src/`
- [ ] Run: `uv run pytest tests/test_support_reflection.py tests/test_context_display.py tests/webui/test_server_parity.py -v`
- [ ] Run: `npm run js:check`
- [ ] Run (slow): `uv run pytest tests/webui/test_support_value_ledger_browser.py -v`


## Files to Modify
- `prds/execution-plan-183-milestone6.md`
- `src/alfred/support_reflection.py`
- `src/alfred/context_display.py`
- `src/alfred/interfaces/webui/static/js/components/context-viewer.js`
- `docs/websocket-protocol.md`
- `tests/test_support_reflection.py`
- `tests/test_context_display.py` (or a new narrow serialization test)
- `tests/webui/test_support_value_ledger_browser.py`


## Commit Strategy
Keep this slice atomic:
- `feat(prd-183): webui renders v2 support value ledger in context viewer`
