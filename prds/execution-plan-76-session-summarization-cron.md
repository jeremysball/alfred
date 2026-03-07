# Execution Plan: PRD #76 - Session Summarization with Cron

**Branch:** `feature/prd-76-session-summarization-cron`
**Created:** 2026-03-06

---

## Phase 1: Session ID Tagging Infrastructure

### Session ID Data Model

- [ ] **Test:** `test_memory_entry_has_session_id_field()` - verify MemoryEntry accepts session_id
  - **Commit:** `test(memory): verify MemoryEntry accepts session_id field`
  
- [ ] **Implement:** Add `session_id: str` field to `MemoryEntry` dataclass
  - **Commit:** `feat(memory): add session_id field to MemoryEntry dataclass`

- [ ] **Test:** `test_assign_session_id_creates_new_when_none()` - new session when no current session
  - **Commit:** `test(session): verify assign_session_id creates new session when none exists`

- [ ] **Test:** `test_assign_session_id_continues_within_threshold()` - continues existing session within 30 min gap
  - **Commit:** `test(session): verify session continues within 30 minute threshold`

- [ ] **Test:** `test_assign_session_id_creates_new_after_threshold()` - new session after 30 min idle
  - **Commit:** `test(session): verify new session created after 30 minute idle threshold`

- [ ] **Implement:** Create `assign_session_id()` function with 30-minute threshold logic
  - **Commit:** `feat(session): implement assign_session_id with 30min threshold`

### Session Metadata Tracking

- [ ] **Test:** `test_session_metadata_tracks_message_count()` - verify message_count increments
  - **Commit:** `test(session): verify session metadata tracks message count`

- [ ] **Test:** `test_session_metadata_tracks_timestamp_range()` - verify first/last message times
  - **Commit:** `test(session): verify session metadata tracks timestamp range`

- [ ] **Implement:** Create `SessionMetadata` dataclass with message_count, first_message_time, last_message_time
  - **Commit:** `feat(session): create SessionMetadata dataclass for tracking`

---

## Phase 2: Session Storage Infrastructure

### Directory Structure

- [ ] **Test:** `test_sessions_dir_created_on_init()` - verify `data/sessions/` directory created
  - **Commit:** `test(storage): verify sessions directory created on initialization`

- [ ] **Implement:** Create `ensure_sessions_dir()` function in storage module
  - **Commit:** `feat(storage): create ensure_sessions_dir for session storage`

- [ ] **Test:** `test_session_folder_created_for_new_session()` - verify `{session_id}/` folder created
  - **Commit:** `test(storage): verify session folder created for new session`

- [ ] **Implement:** Create `create_session_folder(session_id)` function
  - **Commit:** `feat(storage): implement create_session_folder for session isolation`

### Session Messages Storage

- [ ] **Test:** `test_store_session_message_writes_to_jsonl()` - verify message written to `{session_id}/messages.jsonl`
  - **Commit:** `test(storage): verify session messages written to jsonl`

- [ ] **Implement:** Create `store_session_message(session_id, message)` function
  - **Commit:** `feat(storage): implement store_session_message for session persistence`

- [ ] **Test:** `test_get_session_messages_returns_all_messages()` - verify retrieval returns list
  - **Commit:** `test(storage): verify get_session_messages returns all messages`

- [ ] **Implement:** Create `get_session_messages(session_id)` function
  - **Commit:** `feat(storage): implement get_session_messages retrieval`

---

## Phase 3: Session Summary Storage

### Summary Data Model

- [ ] **Test:** `test_session_summary_has_required_fields()` - verify SessionSummary dataclass fields
  - **Commit:** `test(summary): verify SessionSummary has all required fields`

- [ ] **Implement:** Create `SessionSummary` dataclass (id, session_id, timestamp, message_range, message_count, summary_text, embedding, version, last_summarized_count)
  - **Commit:** `feat(summary): create SessionSummary dataclass`

- [ ] **Test:** `test_session_summary_serialization_roundtrip()` - verify to/from JSON works
  - **Commit:** `test(summary): verify SessionSummary serialization roundtrip`

- [ ] **Implement:** Add `to_json()` and `from_json()` methods to SessionSummary
  - **Commit:** `feat(summary): add JSON serialization for SessionSummary`

### Summary Storage Operations

- [ ] **Test:** `test_store_summary_writes_to_json_file()` - verify writes to `{session_id}/summary.json`
  - **Commit:** `test(summary): verify summary written to json file`

- [ ] **Implement:** Create `store_summary(summary)` function
  - **Commit:** `feat(summary): implement store_summary persistence`

- [ ] **Test:** `test_get_summary_returns_existing_summary()` - verify retrieval works
  - **Commit:** `test(summary): verify get_summary returns existing summary`

- [ ] **Test:** `test_get_summary_returns_none_when_missing()` - verify None when no summary
  - **Commit:** `test(summary): verify get_summary returns None when missing`

- [ ] **Implement:** Create `get_summary(session_id)` function
  - **Commit:** `feat(summary): implement get_summary retrieval`

- [ ] **Test:** `test_store_summary_increments_version()` - verify version increments on replacement
  - **Commit:** `test(summary): verify summary version increments on replacement`

- [ ] **Implement:** Update `store_summary()` to increment version based on existing summary
  - **Commit:** `feat(summary): implement version increment on summary replacement`

---

## Phase 4: Summary Generation

### LLM Summarization

- [x] ~~**Test:** `test_summarize_conversation_calls_llm()` - verify llm.summarize_conversation invoked with messages~~ ✅
  - **Commit:** `test(llm): verify summarize_conversation calls LLM with messages`

- [x] ~~**Implement:** Create `summarize_conversation(messages)` LLM interface function~~ ✅
  - **Commit:** `feat(llm): implement summarize_conversation interface`

- [x] ~~**Test:** `test_summarize_conversation_returns_summary_text()` - verify returns string summary~~ ✅
  - **Commit:** `test(llm): verify summarize_conversation returns summary text`

- [x] ~~**Implement:** Add LLM prompt and parsing for conversation summarization~~ ✅
  - **Commit:** `feat(llm): add conversation summarization prompt`

### Summary Generation Pipeline

- [x] ~~**Test:** `test_generate_session_summary_creates_embedding()` - verify embedding created for summary~~ ✅
  - **Commit:** `test(summary): verify generate_session_summary creates embedding`

- [x] ~~**Implement:** Create `generate_session_summary(session)` async function~~ ✅
  - **Commit:** `feat(summary): implement generate_session_summary pipeline`

- [x] ~~**Test:** `test_generate_session_summary_uses_existing_summary_id()` - verify ID reuse on regeneration~~ ✅
  - **Commit:** `test(summary): verify generate_session_summary reuses existing summary ID`

- [x] ~~**Implement:** Update `generate_session_summary` to check for existing and reuse ID~~ ✅
  - **Commit:** `feat(summary): reuse existing summary ID on regeneration`

- [x] ~~**Test:** `test_generate_session_summary_sets_correct_message_range()` - verify message_range accurate~~ ✅
  - **Commit:** `test(summary): verify generate_session_summary sets correct message range`

- [x] ~~**Implement:** Set message_range to (0, len(messages)) in generate_session_summary~~ ✅
  - **Commit:** `feat(summary): set full message range in summary generation`

---

## Phase 5: Cron Job - Session Detection

### Active Session Detection

- [x] ~~**Test:** `test_get_active_sessions_returns_sessions_with_messages()` - verify filters to active only~~ ✅
  - **Commit:** `test(cron): verify get_active_sessions returns only active sessions`

- [x] ~~**Implement:** Create `get_active_sessions()` function to scan sessions directory~~ ✅
  - **Commit:** `feat(cron): implement get_active_sessions scanning`

- [x] ~~**Test:** `test_get_active_sessions_includes_message_counts()` - verify metadata loaded~~ ✅
  - **Commit:** `test(cron): verify get_active_sessions includes message counts`

- [x] ~~**Implement:** Load session metadata (total_messages, last_message_time) in get_active_sessions~~ ✅
  - **Commit:** `feat(cron): load session metadata in get_active_sessions`

### Summarization Trigger Logic

- [ ] **Test:** `test_should_summarize_returns_true_when_idle_threshold_met()` - 30 min idle triggers
  - **Commit:** `test(cron): verify should_summarize true when idle > 30 min`

- [ ] **Test:** `test_should_summarize_returns_true_when_message_threshold_met()` - 20 new messages triggers
  - **Commit:** `test(cron): verify should_summarize true when 20+ new messages`

- [ ] **Test:** `test_should_summarize_returns_false_when_below_thresholds()` - neither threshold met
  - **Commit:** `test(cron): verify should_summarize false when below thresholds`

- [ ] **Implement:** Create `should_summarize(session)` function with threshold logic
  - **Commit:** `feat(cron): implement should_summarize threshold logic`

---

## Phase 6: Cron Job - Main Loop

### Cron Job Implementation

- [ ] **Test:** `test_summarize_sessions_job_calls_get_active_sessions()` - verify session scanning
  - **Commit:** `test(cron): verify summarize_sessions_job scans active sessions`

- [ ] **Implement:** Create `summarize_sessions_job(config)` async function skeleton
  - **Commit:** `feat(cron): create summarize_sessions_job skeleton`

- [ ] **Test:** `test_summarize_sessions_job_filters_by_should_summarize()` - verify filtering logic
  - **Commit:** `test(cron): verify summarize_sessions_job filters by should_summarize`

- [ ] **Implement:** Add filtering loop in summarize_sessions_job using should_summarize
  - **Commit:** `feat(cron): add should_summarize filtering to job`

- [ ] **Test:** `test_summarize_sessions_job_generates_summary_for_eligible()` - verify generation called
  - **Commit:** `test(cron): verify summarize_sessions_job generates summaries`

- [ ] **Implement:** Call generate_session_summary for eligible sessions
  - **Commit:** `feat(cron): wire summary generation into cron job`

### Cron Registration

- [ ] **Test:** `test_cron_job_registered_with_interval()` - verify cron system knows about job
  - **Commit:** `test(cron): verify cron job registered with 5 minute interval`

- [ ] **Implement:** Register `summarize_sessions_job` in cron system with 5-minute interval
  - **Commit:** `feat(cron): register summarize_sessions_job with 5min interval`

- [ ] **Test:** `test_cron_interval_configurable()` - verify interval reads from config
  - **Commit:** `test(config): verify cron interval configurable via config`

- [ ] **Implement:** Add `[session]` config section with `cron_interval_minutes` setting
  - **Commit:** `feat(config): add session.cron_interval_minutes configuration`

---

## Phase 7: Search Sessions Tool

### Session Summary Search

- [ ] **Test:** `test_search_session_summaries_finds_similar()` - verify embedding similarity search
  - **Commit:** `test(search): verify search_session_summaries finds similar summaries`

- [ ] **Implement:** Create `search_session_summaries(query_embedding, sessions_dir, top_k)` function
  - **Commit:** `feat(search): implement search_session_summaries embedding search`

- [ ] **Test:** `test_search_session_summaries_returns_top_k()` - verify limits results
  - **Commit:** `test(search): verify search_session_summaries respects top_k limit`

- [ ] **Implement:** Add top_k limiting to search_session_summaries
  - **Commit:** `feat(search): add top_k limiting to session summary search`

### SearchSessionsTool

- [ ] **Test:** `test_search_sessions_tool_exists()` - verify tool class exists
  - **Commit:** `test(tools): verify SearchSessionsTool class exists`

- [ ] **Implement:** Create `SearchSessionsTool` class with name, description
  - **Commit:** `feat(tools): create SearchSessionsTool class`

- [ ] **Test:** `test_search_sessions_tool_creates_embedding()` - verify query embedding created
  - **Commit:** `test(tools): verify SearchSessionsTool creates query embedding`

- [ ] **Implement:** Add embedding creation in SearchSessionsTool.execute()
  - **Commit:** `feat(tools): add embedding creation to SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_calls_search()` - verify search_session_summaries invoked
  - **Commit:** `test(tools): verify SearchSessionsTool calls search_session_summaries`

- [ ] **Implement:** Wire search_session_summaries into SearchSessionsTool.execute()
  - **Commit:** `feat(tools): wire search into SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_formats_results()` - verify results formatted nicely
  - **Commit:** `test(tools): verify SearchSessionsTool formats results`

- [ ] **Implement:** Add result formatting (session_id, timestamp, summary preview) to tool
  - **Commit:** `feat(tools): add result formatting to SearchSessionsTool`

- [ ] **Test:** `test_search_sessions_tool_registered()` - verify tool available to Alfred
  - **Commit:** `test(tools): verify SearchSessionsTool registered with tool system`

- [ ] **Implement:** Register SearchSessionsTool in tool registry
  - **Commit:** `feat(tools): register SearchSessionsTool in tool registry`

---

## Phase 8: Integration & Configuration

### Configuration

- [ ] **Test:** `test_config_has_session_section()` - verify [session] config section loads
  - **Commit:** `test(config): verify session config section loads`

- [ ] **Implement:** Add `[session]` config section with all settings (summarize_idle_minutes, summarize_message_threshold, cron_interval_minutes)
  - **Commit:** `feat(config): add session configuration section`

- [ ] **Test:** `test_config_default_values_correct()` - verify default values match PRD (30, 20, 5)
  - **Commit:** `test(config): verify session config default values`

- [ ] **Implement:** Set default config values (30 min idle, 20 msg, 5 min cron)
  - **Commit:** `feat(config): set session config default values`

### End-to-End Integration

- [ ] **Test:** `test_message_written_gets_session_id()` - verify full flow: message → session_id → storage
  - **Commit:** `test(integration): verify message flow assigns session_id and stores`

- [ ] **Implement:** Wire session_id assignment into message storage pipeline
  - **Commit:** `feat(integration): wire session_id into message storage pipeline`

- [ ] **Test:** `test_cron_finds_and_summarizes_idle_session()` - verify full cron flow end-to-end
  - **Commit:** `test(integration): verify cron finds and summarizes idle session`

- [ ] **Implement:** Integration test verifying full cron flow
  - **Commit:** `feat(integration): end-to-end cron summarization test`

---

## Phase 9: Documentation & Cleanup

- [ ] **Docs:** Update PRD progress section with completed items
  - **Commit:** `docs(prd): update PRD #76 progress with completed work`

- [ ] **Refactor:** Review and consolidate duplicate code between memory and session storage
  - **Commit:** `refactor(storage): consolidate shared storage utilities`

- [ ] **Test:** Run full test suite `uv run pytest` - all tests pass
  - **Commit:** `chore(tests): verify full test suite passes`

- [ ] **Lint:** Run `uv run ruff check src/` - no issues
  - **Commit:** `style: fix linting issues`

- [ ] **Type Check:** Run `uv run basedpyright src/` - no type errors
  - **Commit:** `types: fix type checking issues`

---

## Summary

| Phase | Tasks | Est. Commits |
|-------|-------|--------------|
| Phase 1: Session ID | 8 | 8 |
| Phase 2: Storage Infra | 8 | 8 |
| Phase 3: Summary Storage | 10 | 10 |
| Phase 4: Summary Generation | 10 | 10 |
| Phase 5: Cron Detection | 8 | 8 |
| Phase 6: Cron Job | 10 | 10 |
| Phase 7: Search Tool | 12 | 12 |
| Phase 8: Integration | 8 | 8 |
| Phase 9: Cleanup | 5 | 5 |
| **Total** | **79** | **79** |

---

## Commit Message Pattern

```
<type>(<scope>): <description>

Types: test, feat, refactor, docs, style, types, chore
Scopes: memory, session, storage, summary, llm, cron, search, tools, config, integration
```

---

## Daily Workflow

```
1. Pick next unchecked task
2. Write test (Red)
3. Run test: uv run pytest <test_file> -v
4. Implement minimum code (Green)
5. Run test again to verify pass
6. Commit with conventional commit format
7. Check off task
8. Repeat
```
