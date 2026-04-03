# Execution Plan: PRD #167 Addendum - Normalize Transcript Messages and Message-ID Evidence Refs

## Overview
This addendum replaces JSON-blob transcript storage with canonical `session_messages` rows. It preserves the public `save_session()` / `load_session()` session API while making transcript message identity relational, rekeying message embeddings to canonical message identity, and switching `EvidenceRef` spans from message indexes to message IDs. It is a prerequisite for PRD #168 Milestone 3 intervention logging.

## Current Repo Constraints
- `src/alfred/storage/sqlite.py` currently persists transcript history in `sessions.messages` as one JSON blob and reconstructs sessions by decoding that blob. The addendum must cut over cleanly to one source of truth rather than dual-writing transcript state.
- `load_session()` and `list_sessions()` already return `{"messages": [...]}` payloads and many callers and tests depend on that public shape. The storage model can change, but the returned session payload must stay stable.
- `src/alfred/session.py` edit and truncation flows rely on stable message IDs and contiguous `idx` ordering, but they persist through `save_session()`. Canonical transcript rows must preserve those behaviors.
- `message_embeddings` currently uses a synthetic `message_embedding_id` based on `session_id` and `message_idx`. The addendum should rekey embeddings to canonical message identity without regressing message search semantics.
- `EvidenceRef` and `support_evidence_refs` currently store `message_start_idx` / `message_end_idx`. The addendum must preserve same-session span semantics while switching to message IDs and composite foreign keys.
- Alfred is a beta product. Prefer the clean B2 cutover the user chose: make `session_messages` canonical, remove `sessions.messages` from schema/runtime, and avoid transition-era dual truth.

## Success Signal
- Alfred persists transcript messages in canonical `session_messages` rows keyed by `(session_id, message_id)` and reconstructs the same session payload from those rows.
- Re-saving edited or truncated history atomically replaces the canonical message rows, removes stale rows, and preserves surviving message IDs and ordering.
- Message embeddings and message search still work after the cutover, but now key off canonical transcript identity instead of synthetic idx-only IDs.
- `EvidenceRef` stores `message_start_id` / `message_end_id` and support-memory episode round-trips retain same-session message-span provenance through real foreign-key-backed transcript rows.

## Validation Workflow
- **Workflow:** Python
- **Static checks:** `uv run ruff check src/ tests/storage/test_session_message_storage.py tests/storage/test_message_embeddings.py tests/storage/test_support_memory_storage.py` and `uv run mypy --strict src/`
- **Targeted tests for this addendum:** `uv run pytest tests/storage/test_session_message_storage.py tests/storage/test_message_embeddings.py tests/storage/test_support_memory_storage.py -v`

---

## Phase 1: PRD #167 addendum - transcript normalization and message-ID evidence

### Canonical transcript row storage

- [x] Test: `test_session_round_trips_through_canonical_session_messages()` - verify `save_session()` persists one ordered row per message in `session_messages`, `load_session()` reconstructs the original payload, and transcript rows, not a session-level JSON blob, are the source of truth.
- [x] Implement: add the canonical `session_messages` table, remove `sessions.messages` from schema/runtime, and rebuild `save_session()` / `load_session()` / `list_sessions()` around ordered transcript rows while preserving the existing returned session payload shape.
- [x] Run: `uv run pytest tests/storage/test_session_message_storage.py::test_session_round_trips_through_canonical_session_messages -v`

### History rewrite replaces canonical rows atomically

- [ ] Test: `test_save_session_replaces_canonical_message_rows_after_history_edit()` - verify re-saving shorter edited history removes stale transcript rows, preserves surviving message IDs, and keeps `message_count` and message order correct.
- [ ] Implement: make `save_session()` replace one session's canonical message rows atomically and keep session metadata synchronized after history edits or truncation.
- [ ] Run: `uv run pytest tests/storage/test_session_message_storage.py::test_save_session_replaces_canonical_message_rows_after_history_edit -v`

### Canonical message identity for embeddings and search

- [ ] Test: `test_save_session_rebuilds_message_embeddings_with_canonical_message_ids()` - verify embeddings and vec rows rebuild against canonical transcript identity after a history rewrite without leaving stale rows behind.
- [ ] Implement: rekey `message_embeddings` and vec storage to canonical transcript identity while preserving existing message-search results by `message_idx`, role, and snippet.
- [ ] Run: `uv run pytest tests/storage/test_message_embeddings.py::TestMessageEmbeddingsIndexing::test_save_session_rebuilds_message_embeddings_with_canonical_message_ids -v`

### EvidenceRef message-ID span contract

- [ ] Test: `test_promoting_session_message_spans_to_message_id_evidence_refs_keeps_session_archive_unchanged()` - verify `EvidenceRef.from_session_message_span()` resolves same-session message-ID spans, preserves excerpt and timestamp behavior, and does not mutate the reconstructed session payload.
- [ ] Implement: switch the `EvidenceRef` contract from `message_start_idx` / `message_end_idx` to `message_start_id` / `message_end_id` while preserving same-session span semantics and helper behavior.
- [ ] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_promoting_session_message_spans_to_message_id_evidence_refs_keeps_session_archive_unchanged -v`

### Support-episode evidence storage with composite transcript FKs

- [ ] Test: `test_episode_and_message_id_evidence_round_trip_through_sqlite_store()` - verify support episodes and evidence refs round-trip through SQLite with message-ID spans backed by canonical transcript rows.
- [ ] Implement: update `support_evidence_refs` storage and support-episode save/load helpers to persist message-ID spans with same-session composite foreign keys to `session_messages`.
- [ ] Run: `uv run pytest tests/storage/test_support_memory_storage.py::test_episode_and_message_id_evidence_round_trip_through_sqlite_store -v`

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - canonical transcript row schema, session save/load/list implementation, message-embedding rekeying, and support-evidence FK updates
2. `src/alfred/memory/support_memory.py` - `EvidenceRef` message-ID span contract and helper updates
3. `src/alfred/session.py` - only if the canonical-storage cutover exposes persistence assumptions in edit/truncate flows
4. `tests/storage/test_session_message_storage.py` - new transcript normalization storage tests
5. `tests/storage/test_message_embeddings.py` - embedding rekey and rebuild coverage
6. `tests/storage/test_support_memory_storage.py` - message-ID evidence promotion and support-episode round-trip coverage
7. `prds/168-adaptive-support-profile-and-intervention-learning.md` - dependency/decision alignment for intervention logging on top of normalized transcript storage
8. `prds/execution-plan-168-milestone3.md` - defer intervention logging until this addendum lands

## Commit Strategy

Each completed test → implement → run block should map cleanly to one atomic commit:
- `refactor(storage): normalize transcript messages into canonical rows`
- `fix(storage): replace canonical transcript rows on history rewrite`
- `refactor(storage): key message embeddings by canonical message identity`
- `refactor(memory): switch evidence refs to message-id spans`
- `feat(memory): persist support evidence against canonical transcript rows`
