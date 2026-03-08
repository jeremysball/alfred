# Execution Plan: PRD #76 - Session Summarization

## Overview
Implement automatic session summarization with SQLite storage, cron job execution, and two-stage search.

---

## Phase 1: SQLite Storage Layer

### 1.1 Create session_summaries table
- [ ] Test: `test_create_session_summaries_table()` - verify table exists with correct schema
- [ ] Implement: Add `_create_session_summaries_table()` method to SQLiteStore
- [ ] Test: `test_session_summaries_foreign_key()` - verify FK constraint to sessions
- [ ] Implement: Add FK constraint with ON DELETE CASCADE

### 1.2 Save summary method
- [ ] Test: `test_save_summary_inserts_new()` - verify insert works
- [ ] Implement: `save_summary(summary: SessionSummary) -> None` method
- [ ] Test: `test_save_summary_with_embedding()` - verify embedding stored as JSON
- [ ] Implement: Serialize embedding to JSON before storage

### 1.3 Get latest summary method
- [ ] Test: `test_get_latest_summary_returns_most_recent()` - query by version desc
- [ ] Implement: `get_latest_summary(session_id: str) -> SessionSummary | None`
- [ ] Test: `test_get_latest_summary_none_exists()` - return None if no summary
- [ ] Implement: Handle missing summary case

### 1.4 Find sessions needing summary
- [ ] Test: `test_find_sessions_needing_summary_by_message_count()` - 20+ new messages
- [ ] Implement: `find_sessions_needing_summary(threshold: int) -> list[str]`
- [ ] Test: `test_find_sessions_needing_summary_by_idle_time()` - 30min idle
- [ ] Implement: Add idle time check to query

---

## Phase 2: SessionSummarizer Integration

### 2.1 Fix SessionSummarizer to use SQLite
- [ ] Test: `test_save_summary_to_sqlite()` - verify save_summary uses SQLite not files
- [ ] Implement: Update `save_summary()` to call `SQLiteStore.save_summary()`
- [ ] Test: `test_load_summary_from_sqlite()` - verify load from SQLite
- [ ] Implement: Update `load_summary()` to query SQLite

### 2.2 LLM integration for generate_summary
- [ ] Test: `test_generate_summary_calls_llm()` - verify LLM client invoked
- [ ] Implement: Call LLM chat completion with conversation preview
- [ ] Test: `test_generate_summary_creates_embedding()` - verify embedder called
- [ ] Implement: Generate embedding via embedder.embed()

---

## Phase 3: Cron Job Wiring

### 3.1 Update system job code
- [ ] Test: `test_cron_job_finds_eligible_sessions()` - job queries for sessions
- [ ] Implement: Update `session_summarizer` system job in `system_jobs.py`
- [ ] Test: `test_cron_job_generates_summary()` - job calls summarizer
- [ ] Implement: Wire up SessionSummarizer in job context
- [ ] Test: `test_cron_job_saves_to_sqlite()` - verify persistence
- [ ] Implement: Store generated summary via SQLiteStore

---

## Phase 4: Two-Stage Search Implementation

### 4.1 Stage 1: Find relevant sessions
- [ ] Test: `test_find_relevant_sessions_by_embedding()` - semantic search on summaries
- [ ] Implement: `_find_relevant_sessions(query: str, top_k: int) -> list[Session]`
- [ ] Test: `test_find_relevant_sessions_min_similarity()` - filter by threshold
- [ ] Implement: Add similarity threshold filtering

### 4.2 Stage 2: Search within sessions
- [ ] Test: `test_search_session_messages()` - find messages by similarity
- [ ] Implement: `_search_session_messages(session_id: str, query: str, top_k: int)`
- [ ] Test: `test_search_session_messages_embedding_match()` - verify embedding search
- [ ] Implement: Compare query embedding to message embeddings

### 4.3 Wire up SearchSessionsTool
- [ ] Test: `test_search_sessions_two_stage()` - full two-stage flow
- [ ] Implement: Update `execute_stream()` to use both stages
- [ ] Test: `test_search_sessions_formats_output()` - verify output format
- [ ] Implement: Format hierarchical results (session → messages)

---

## Phase 5: Integration & Testing

### 5.1 Register tool with dependencies
- [ ] Test: `test_search_sessions_tool_registered()` - tool in registry
- [ ] Implement: Ensure `register_builtin_tools()` passes llm_client
- [ ] Test: `test_llm_client_passed_to_summarizer()` - verify dependency injection
- [ ] Implement: Pass llm_client in `alfred.py`

### 5.2 End-to-end test
- [ ] Test: `test_e2e_create_session_summarize_search()` - full flow
- [ ] Implement: Integration test with real components
- [ ] Test: `test_e2e_summary_regeneration()` - version increment on re-summarize
- [ ] Implement: Verify version tracking works

---

## Files to Modify

1. `src/alfred/storage/sqlite.py` - Add session_summaries table and methods
2. `src/alfred/tools/search_sessions.py` - Fix to use SQLite, implement two-stage search
3. `src/alfred/cron/system_jobs.py` - Wire up summarization logic
4. `src/alfred/tools/__init__.py` - Pass llm_client to SearchSessionsTool
5. `src/alfred/alfred.py` - Pass llm_client to register_builtin_tools

---

## Commit Strategy

Each checkbox = one atomic commit following conventional commits:
- `feat(storage): add session_summaries table`
- `feat(storage): implement save_summary method`
- `feat(summarizer): integrate LLM for summary generation`
- `feat(cron): wire up session summarization job`
- `feat(search): implement two-stage session search`
