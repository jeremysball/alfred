# PRD: Cosine Similarity Migration for Memory and Session Search

**GitHub Issue**: [#143](https://github.com/jeremysball/alfred/issues/143)  
**Status**: Ready  
**Priority**: High  
**Created**: 2026-03-21  
**Last Updated**: 2026-03-21

---

## 1. Summary

Fix Alfred’s vector-search semantics so memory retrieval and session retrieval both operate on a single, explicit contract:

- sqlite-vec indexes are configured for **cosine distance**
- Alfred callers consume **higher-is-better similarity values**, not raw backend distance values
- existing vector indexes can be **rebuilt safely** when the metric contract changes
- Web UI memory save/recall/reload behavior is covered by regression tests

This PRD intentionally treats memory search and session search as one unit of work. The bug is not feature-specific. It is a search-contract problem that spans both retrieval paths.

---

## 2. Problem Statement

Alfred’s current sqlite-vec search layer has a semantics mismatch.

### What the backend does today
Current vector queries return a backend distance value from sqlite-vec.

### What Alfred assumes today
Application code treats that returned value like a similarity score:
- **higher** means better
- threshold checks use names like `min_similarity`
- formatting shows the value as user-facing “relevance”

### Why this is broken
A distance value and a similarity value are not interchangeable.

This creates real retrieval bugs:
- memory search can filter out the best match because low distance is incorrectly treated as low similarity
- session search can rank or filter summaries/messages using the wrong direction
- UI and tool output can present misleading “relevance” values
- future work on persistent memory, session recall, and Web UI search behavior builds on a faulty foundation

This is a correctness bug in the retrieval layer, not a tuning issue.

---

## 3. Current-State Audit

The current mismatch is visible in the codebase.

### Storage layer
`src/alfred/storage/sqlite.py`
- `search_memories()` selects `e.distance` and returns it as `similarity`
- `search_summaries()` selects `v.distance as similarity`
- `search_session_messages()` selects `v.distance as similarity`
- vec0 tables are created without an explicit metric contract beyond dimension

### Memory context path
`src/alfred/context.py`
- `ContextBuilder.search_memories()` reads `similarity` from store results
- it filters with `if similarity < self.min_similarity`
- it computes hybrid score as if bigger similarity is better
- it sorts by descending score

That logic only makes sense if the returned value is an actual higher-is-better similarity.

### Session search path
`src/alfred/tools/search_sessions.py`
- `SearchSessionsTool.execute_stream()` reads `summary["similarity"]`
- it filters with `if similarity < self.min_similarity`
- it prints user-facing “Relevance” values from that field

Again, this assumes a higher-is-better similarity contract.

### Memory store wrapper
`src/alfred/memory/sqlite_store.py`
- forwards the store’s returned `similarity` value directly into higher-level memory search results
- therefore inherits any storage-layer metric confusion unchanged

---

## 4. Goals

1. Make memory search and session search use one explicit cosine-based retrieval contract.
2. Ensure Alfred callers receive **similarity**, not raw backend distance mislabeled as similarity.
3. Configure sqlite-vec indexes consistently for cosine distance.
4. Add a safe rebuild path for vec0 indexes when metric/schema contract changes.
5. Keep existing higher-level thresholds (`min_similarity`) meaningful.
6. Add regression coverage for user-visible memory recall behavior in the Web UI.

---

## 5. Non-Goals

- redesigning Alfred’s memory architecture
- replacing sqlite-vec with another vector backend
- changing embedding providers or embedding dimensions as part of this PRD
- redesigning the Web UI memory experience beyond correctness coverage
- introducing backward compatibility for callers that depend on raw backend distance values

---

## 6. User and System Impact

### User impact
Users should see:
- more reliable memory recall
- more reliable session recall
- stable relevance thresholds
- Web UI remember → recall → reload behavior that does not regress based on index semantics

### System impact
The system gains:
- one retrieval contract across memory and session search
- explicit vec schema semantics, not implicit defaults
- safer migration behavior when the vector schema changes
- clearer tests that describe ranking behavior instead of merely exercising SQL

---

## 7. Architecture Decisions

### Decision 1: Alfred’s public search contract is similarity-first
At Alfred’s application boundary, search results must expose:
- `similarity`: higher is better
- values suitable for thresholding and user-facing relevance output

The storage layer may work with backend-specific distances internally, but callers must not.

### Decision 2: The storage layer owns metric translation
`SQLiteStore` is the boundary between sqlite-vec’s raw metric behavior and Alfred’s higher-level search semantics.

That means:
- raw `distance` stays internal to storage helpers
- conversion to Alfred-facing `similarity` happens before returning search results
- memory and session search must use the same conversion rule

### Decision 3: Vec0 schema contract includes both dimension and metric
Today the code checks vec table dimension drift. After this PRD, the vector schema contract must include:
- embedding dimension
- distance metric
- rebuild expectation when the contract drifts

A vec table with the right dimension but the wrong metric is still wrong.

### Decision 4: Rebuild is explicit and safe
A full rebuild is acceptable for this PRD.

The migration path should:
- recreate vec tables using the new cosine contract
- repopulate vector rows deterministically
- fail fast if the store cannot guarantee a correct rebuilt index

### Decision 5: Behavior tests outrank internal logic tests
Because the bug is user-visible retrieval correctness, verification must include:
- storage tests for returned semantics
- integration tests for memory/session search behavior
- Web UI/browser behavior for remember → recall → reload

---

## 8. Target Contract

### 8.1 Alfred-facing search result contract
Every Alfred search path that today exposes `similarity` must satisfy:

```python
{
    "similarity": float,  # higher is better
}
```

This applies to:
- memory search results
- session summary search results
- session message search results

### 8.2 Threshold contract
Existing threshold names such as `min_similarity` remain valid.

Callers should be able to keep logic like:
- `if similarity < min_similarity: skip`

without caring about sqlite-vec’s native metric direction.

### 8.3 Ranking contract
Callers may sort descending by `similarity` or by composite scores derived from it.

That means the storage layer must not return a lower-is-better value in a field named `similarity`.

---

## 9. Proposed Technical Design

### 9.1 Add explicit vec table metric handling
Extend the sqlite-vec table management logic so the schema contract is not only “FLOAT[N] exists” but also “this table was created for cosine semantics.”

Likely touchpoint:
- `src/alfred/storage/sqlite.py`

Expected work:
- introduce vec table schema inspection that can detect metric drift as well as dimension drift
- centralize vec table creation so all relevant tables use the same metric contract
- cover all Alfred vec tables:
  - `memory_embeddings`
  - `session_summaries_vec`
  - `message_embeddings_vec`

### 9.2 Normalize backend distance to Alfred similarity
Storage-layer query methods should stop returning raw distance values as `similarity`.

Expected work:
- keep backend `distance` internal
- convert raw vector results into Alfred-facing `similarity`
- apply that consistently in:
  - `search_memories()`
  - `search_summaries()`
  - `search_session_messages()`

### 9.3 Keep memory and session paths aligned
Memory and session search must share one semantics rule.

That means:
- no one-off conversion logic in `ContextBuilder`
- no separate interpretation logic in `SearchSessionsTool`
- storage helpers should already return values that higher-level code can trust

### 9.4 Rebuild existing vector indexes safely
The rebuild flow must support current SQLite data.

Expected behavior:
- detect metric drift on initialization or explicit rebuild entry point
- recreate vec tables using the cosine contract
- repopulate index rows from canonical sources

Canonical rebuild sources should be:
- `memories.content` via embedder when needed
- `session_summaries.embedding` or `session_summaries.summary_text`
- `message_embeddings.embedding` or canonical message text/snippet source already stored by Alfred

The implementation may choose the cheapest safe source per table, but the end result must be a fully rebuilt cosine index.

### 9.5 Fail fast on contract mismatch
If Alfred detects a vector schema mismatch it cannot repair safely, it should fail with a clear error rather than serving misleading search results.

---

## 10. Likely Files to Change

### Core implementation
- `src/alfred/storage/sqlite.py` — vec schema inspection, table creation, search normalization, rebuild flow
- `src/alfred/memory/sqlite_store.py` — preserve corrected similarity semantics through the memory-store wrapper
- `src/alfred/context.py` — verify hybrid scoring and filtering still operate on true similarity
- `src/alfred/tools/search_sessions.py` — verify session filtering/output now reflect corrected similarity semantics

### Tests
- `tests/storage/test_sqlite_vec.py` — vec schema contract tests for dimension + metric drift
- `tests/storage/` new similarity-semantics tests for memory/session search
- `tests/test_context_memory_scoring.py` or similar — memory-context threshold/ranking behavior
- `tests/test_search_sessions_integration.py` and/or `tests/tools/test_search_sessions.py` — session threshold/ranking behavior
- `tests/webui/` — browser or websocket-level remember → recall → reload regression coverage

### Docs
- `prds/143-cosine-similarity-migration.md`
- optional docs/comments near vector-store internals if needed to clarify the new contract

---

## 11. Acceptance Criteria

### Storage contract
- [ ] vec0 tables are created with an explicit cosine metric contract
- [ ] vec schema validation covers both dimension and metric drift
- [ ] storage search methods no longer expose raw distance values as `similarity`

### Memory search behavior
- [ ] `ContextBuilder.search_memories()` receives higher-is-better similarity values
- [ ] `min_similarity` filtering behaves correctly for memory retrieval
- [ ] hybrid memory scoring/ranking behaves correctly after normalization

### Session search behavior
- [ ] session summary search exposes higher-is-better similarity
- [ ] session message search exposes higher-is-better similarity
- [ ] `SearchSessionsTool` thresholding and output behave correctly

### Rebuild behavior
- [ ] existing vec indexes can be rebuilt into cosine-configured tables
- [ ] rebuilt indexes preserve correct search behavior
- [ ] unrecoverable schema mismatch fails clearly

### User-visible verification
- [ ] Web UI remember → recall → reload regression coverage passes
- [ ] full verification passes with no similarity/distance contract leaks

---

## 12. Milestones

### Milestone 1: Lock the contract with failing tests
Codify the intended search semantics before changing the implementation.

Validation:
- failing tests prove that raw distance is currently being treated as similarity
- tests cover memory search, session summary search, and session message search

### Milestone 2: Add vec schema metric awareness
Teach the storage layer to detect and create vec tables with the intended cosine contract.

Validation:
- dimension + metric drift are both detectable
- vec table creation is centralized and consistent

### Milestone 3: Migrate memory search to the new contract
Make memory search return real Alfred-facing similarity values.

Validation:
- storage memory search exposes corrected similarity
- `ContextBuilder` thresholding and hybrid scoring behave correctly

### Milestone 4: Migrate session search to the new contract
Apply the same semantics to session summary and session message retrieval.

Validation:
- `search_summaries()` and `search_session_messages()` expose corrected similarity
- `SearchSessionsTool` thresholding/output are correct

### Milestone 5: Add safe rebuild and startup validation
Rebuild existing indexes into cosine-configured vec tables and fail fast on unrecoverable drift.

Validation:
- rebuild logic repopulates all affected vec tables safely
- startup or explicit validation detects incorrect schema state

### Milestone 6: Add Web UI regression coverage and finalize verification
Verify the user-visible remember → recall → reload path and complete the final verification sweep.

Validation:
- Web UI/browser regression passes
- repo verification commands pass
- docs describe the new contract clearly

---

## 13. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Metric migration fixes SQL but not caller semantics | High | Keep storage as the only translation boundary and verify behavior in higher-level tests |
| Rebuild logic drops vec rows without repopulating them | High | Add rebuild tests per vec table and fail fast if repopulation cannot complete |
| Memory and session search drift into different similarity rules | High | Use one shared normalization rule and one PRD for both paths |
| Existing thresholds become meaningless after migration | Medium | Keep Alfred-facing `similarity` as the stable contract and verify threshold behavior with tests |
| Web UI still appears flaky despite storage fixes | Medium | Add remember → recall → reload regression coverage through the public interface |
| Metric drift is silently ignored in future schema changes | Medium | Extend schema validation to cover metric, not just dimension |

---

## 14. Validation Strategy

### Required checks
- targeted storage tests for similarity semantics
- targeted integration tests for memory and session search behavior
- Web UI/browser regression for remember → recall → reload
- `uv run ruff check src/ tests/`
- `uv run mypy --strict src/`
- `uv run pytest`

### Definition of done
This PRD is done when:
- Alfred no longer labels backend distance as similarity
- memory and session search share one cosine-based semantics contract
- vec schema validation and rebuild behavior are safe and explicit
- user-visible memory recall behavior remains correct across reload

---

## 15. Related Documents

- `docs/prds/done/117-unified-sqlite-storage-system.md`
- `docs/prds/done/102-unified-memory-system.md`
- `docs/prds/done/76-session-summarization-cron.md`
- `prds/135-persistent-memory-context.md`

---

## 16. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-21 | Keep memory and session search in one PRD | The bug is a shared retrieval-contract problem |
| 2026-03-21 | Make the storage layer own metric translation | Callers should not reason about backend distance quirks |
| 2026-03-21 | Treat vec schema metric as part of the contract | Correct dimension alone is not enough |
| 2026-03-21 | Full rebuild is acceptable | Simpler and safer than preserving a wrong metric contract in place |
| 2026-03-21 | Require Web UI behavior coverage | The bug is user-visible and must be verified end to end |
