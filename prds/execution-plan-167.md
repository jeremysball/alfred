# Execution Plan: PRD #167 - Support Memory Foundation

## Overview
Milestone 1 was completed by the documentation-first rewrite of PRD #167 and the umbrella support-model work. This execution plan starts at the first code-bearing milestone: durable typed support memory anchored to existing transcript sessions. The plan preserves current session search and curated memory behavior while introducing structured operational state one seam at a time: episode/evidence storage, life domains/arcs, arc-linked work objects, derived situations, then operational-first retrieval and docs alignment.

## Current Repo Constraints
- `src/alfred/storage/sqlite.py` is already the single persistence boundary for sessions, summaries, memories, and cron. Adding a second persistence path would duplicate transactions, initialization rules, and storage behavior.
- Transcript sessions are currently stored as JSON blobs in `sessions.messages`; support memory must point back to session/message provenance without rewriting that archive contract or breaking existing session load/save flows.
- `src/alfred/session.py` and `SessionManager` still treat sessions as the active runtime container for CLI/Web UI flows. PRD #167 must demote session semantics without breaking `new_session`, `resume_session`, truncation, or message embedding behavior.
- `src/alfred/context.py` currently assembles context from managed markdown, curated memories, session history, and tool outcomes. There is no operational-first retrieval seam yet, so the plan must add one without regressing current memory and session-search behavior.
- Session and memory search already have tested similarity semantics and active callers. PRD #167 must preserve those recall paths as provenance/fallback rather than silently replacing them.
- Prior docs and PRD alignment work is already committed on this branch. Implementation should stay tightly scoped to Python memory, session, and context surfaces plus the directly affected docs/templates.

## Success Signal
- Alfred can persist and reload typed episodes, evidence refs, life domains, operational arcs, and arc-linked work state through the existing SQLite boundary.
- A fresh session can resolve an existing arc or broad situation from structured state first, then fall back to archive evidence only when provenance or recall is needed.
- Questions like "what is active?", "what's blocked?", and "what decision is still open?" can be answered from structured operational state instead of session search alone.
- Session search still works for provenance and recall flows.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/storage/test_support_memory_storage.py tests/test_support_memory_context.py` and `uv run mypy --strict src/`
- **Targeted tests for this PRD phase plan:**
  - `uv run pytest tests/storage/test_support_memory_storage.py -v`
  - `uv run pytest tests/test_support_memory_context.py -v`
  - expand to adjacent existing session/context tests only when a phase changes those public seams

---

## Phase 1: Milestone 2 - Add typed interaction episodes and evidence refs

### Episode and evidence storage contract

- [x] Test: `test_episode_and_evidence_round_trip_through_sqlite_store()` - verify two episodes anchored to one transcript session preserve stable IDs, schema version, dominant need/context, arc/domain links, and evidence message refs after save/load.
- [x] Implement: add typed support-memory models plus SQLite tables and store methods for episode and evidence-ref persistence, keeping transcript sessions as provenance rather than copying transcript content into the new records.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_episode_and_evidence_round_trip_through_sqlite_store -v`

### Session-backed evidence promotion

- [x] Test: `test_promoting_session_message_ranges_to_evidence_refs_keeps_session_archive_unchanged()` - verify creating evidence refs from persisted session messages uses transcript IDs or ranges as provenance and leaves the stored session payload unchanged.
- [x] Implement: add the minimal session-support helper that builds evidence refs from existing persisted message IDs or ranges without mutating the session archive contract.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_promoting_session_message_ranges_to_evidence_refs_keeps_session_archive_unchanged -v`

---

## Phase 2: Milestone 3 - Add life domains and operational arcs

### Domain and arc round-trip

- [x] Test: `test_life_domain_and_operational_arc_round_trip_without_session_search()` - verify a work domain and linked project arc can be created, updated, and reloaded without touching archive search paths.
- [x] Implement: add life-domain and operational-arc models, tables, and store methods with status, salience, timestamps, linked evidence refs, and domain relationships.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_life_domain_and_operational_arc_round_trip_without_session_search -v`

### Resume-oriented arc listing

- [x] Test: `test_active_arcs_are_listed_in_resume_order_for_a_domain()` - verify structured state can list active or dormant arcs by salience and recent activity for resume and orient flows.
- [x] Implement: add the minimal query helper for domain-scoped active arcs and recent-activity ordering without introducing session-search fallback at this seam.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_active_arcs_are_listed_in_resume_order_for_a_domain -v`

---

## Phase 3: Milestone 4 - Add project/task/open-loop operational state

### Operational work-state persistence

- [x] Test: `test_arc_operational_state_round_trips_tasks_blockers_decisions_and_open_loops()` - verify arc-linked work objects persist status, next step or tension, timestamps, and evidence refs.
- [x] Implement: add storage and typed records for tasks, blockers, decisions, and open loops linked to operational arcs.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_arc_operational_state_round_trips_tasks_blockers_decisions_and_open_loops -v`

### Arc snapshot composition

- [x] Test: `test_arc_snapshot_reads_structured_work_state_without_transcript_search()` - verify runtime can load one composed arc view with its tasks, blockers, open loops, and decisions without reconstructing from session history.
- [x] Implement: add a composed arc reader for context and session-start callers that assembles operational state from the new tables.
- [x] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_arc_snapshot_reads_structured_work_state_without_transcript_search -v`

---

## Phase 4: Milestone 5 - Add derived situation objects and operational-first retrieval

### Arc situation freshness

- [ ] Test: `test_stale_arc_situation_refreshes_from_arc_state_and_recent_episodes()` - verify stale `ArcSituation` data is recomputed from structured arc state plus recent episode evidence before it is reused.
- [ ] Implement: add derived situation models, storage, freshness metadata, and a minimal refresh path for `ArcSituation`.
- [ ] Run: `uv run pytest tests/test_support_memory_context.py::test_stale_arc_situation_refreshes_from_arc_state_and_recent_episodes -v`

### Session-start resume retrieval

- [ ] Test: `test_fresh_session_resume_context_prefers_arc_state_and_episodes_before_session_search()` - verify a new session opening message that matches an existing arc gets operational state and recent episode evidence loaded before archive recall is consulted.
- [ ] Implement: add an operational-first retrieval seam in `src/alfred/context.py` or a thin support-context helper plus explicit resume payload data for cross-session continuity.
- [ ] Run: `uv run pytest tests/test_support_memory_context.py::test_fresh_session_resume_context_prefers_arc_state_and_episodes_before_session_search -v`

### Broad orientation fallback

- [ ] Test: `test_orientation_message_without_arc_match_uses_global_situation_before_archive_recall()` - verify a broad orientation opening such as "what is active right now?" uses `GlobalSituation` first and only reaches for session search when provenance is needed.
- [ ] Implement: add `GlobalSituation` derivation or refresh and integrate it into the same operational-first retrieval seam without narrating internal bookkeeping.
- [ ] Run: `uv run pytest tests/test_support_memory_context.py::test_orientation_message_without_arc_match_uses_global_situation_before_archive_recall -v`

---

## Phase 5: Milestone 6 - Regression coverage, documentation, and prompt/template updates

### Active-work regression alignment

- [ ] Test: `test_active_work_questions_resolve_from_structured_operational_state()` - verify Alfred can answer active-work and unresolved-loop questions from domains, arcs, and work objects without raw session search being the only source.
- [ ] Implement: close any remaining gaps in the structured retrieval path exposed by the regression while keeping session search as provenance and fallback only.
- [ ] Run: `uv run pytest tests/test_support_memory_context.py::test_active_work_questions_resolve_from_structured_operational_state -v`

### Documentation and managed instruction alignment

- [ ] Implement: update `docs/MEMORY.md`, `docs/ARCHITECTURE.md`, `docs/relational-support-model.md`, `templates/SYSTEM.md`, and `templates/AGENTS.md` to describe transcript sessions vs episodes vs arcs, operational-first retrieval, evidence refs, and session-search demotion consistently with the shipped behavior.
- [ ] Run: `uv run ruff check src/ tests/storage/test_support_memory_storage.py tests/test_support_memory_context.py && uv run mypy --strict src/ && uv run pytest tests/storage/test_support_memory_storage.py tests/test_support_memory_context.py -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - support-memory tables plus persistence and query methods
2. `src/alfred/memory/base.py` or a new support-memory models module under `src/alfred/memory/` - typed records for episodes, evidence refs, domains, arcs, work objects, and situations
3. `src/alfred/memory/__init__.py` - export any new support-memory models or helpers
4. `src/alfred/session.py` - session-backed evidence promotion and transcript provenance helpers
5. `src/alfred/context.py` - operational-first retrieval, resume loading, and broad orientation loading
6. `tests/storage/test_support_memory_storage.py` - storage and composed-read contracts for episodes, evidence, domains, arcs, and work state
7. `tests/test_support_memory_context.py` - retrieval, freshness, resume, and orientation behavior
8. `docs/MEMORY.md` - support-memory layer responsibilities and retrieval order
9. `docs/ARCHITECTURE.md` - runtime flow and source-of-truth boundaries for support memory
10. `docs/relational-support-model.md` - operational explanation of domains, arcs, episodes, and situations
11. `templates/SYSTEM.md` - managed instructions for operational-first retrieval and support-memory roles
12. `templates/AGENTS.md` - execution and retrieval guidance that depends on the shipped memory model

## Commit Strategy

Each completed test → implement → run block should become one atomic commit:
- `feat(memory): add episode and evidence support-memory storage`
- `feat(memory): add domains and operational arcs`
- `feat(memory): add arc-linked work state`
- `feat(context): prefer operational state for resume and orient`
- `docs(memory): align support-memory architecture and instructions`
