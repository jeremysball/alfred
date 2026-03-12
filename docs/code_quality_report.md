# Code Quality Report: Dead Code, Cruft, and Poor Quality Tests

Generated: March 8, 2025

---

## Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| Dead Code (unused variables/functions/classes) | 120+ | Medium |
| Poor Quality Tests | 8 | High |
| Skipped Tests | 6 | Medium |
| Empty/Minimal Files | 10 | Low |
| Total Issues | 144 | - |

---

## Dead Code and Cruft

### Unused Imports (High Confidence)

| File | Line | Issue |
|------|------|-------|
| `src/alfred/cron/notifier.py:12` | `NotificationBuffer` imported but never used (90% confidence) |

### Unused Variables (100% Confidence)

| File | Line | Variable | Context |
|------|------|----------|---------|
| `src/alfred/context.py:276` | `max_tokens` | Function local variable never used |

### Unused Classes, Methods, and Functions (60-90% Confidence)

#### Cron System

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/cron/nlp_parser.py:22` | `NaturalLanguageCronParser` | Class | Complete class unused |
| `src/alfred/cron/nlp_parser.py:414` | `clarify` | Method | Unused method |
| `src/alfred/cron/notifier.py:17` | `NotifierError` | Class | Exception class unused |
| `src/alfred/cron/notifier.py:69` | `CLINotifier` | Class | Complete class unused |
| `src/alfred/cron/notifier.py:193` | `TelegramNotifier` | Class | Complete class unused |
| `src/alfred/cron/notifier.py:101` | `set_buffer` | Method | Never called |
| `src/alfred/cron/notifier.py:109` | `set_toast_manager` | Method | Never called |
| `src/alfred/cron/notifier.py:171` | `flush_buffer` | Method | Never called |
| `src/alfred/cron/observability.py:109` | `log_warning` | Method | Never called |
| `src/alfred/cron/parser.py:38` | `get_next_run` | Function | Never called |
| `src/alfred/cron/store.py:118` | `get_job_history` | Method | Never called |
| `src/alfred/cron/system_jobs.py:18` | `session_store` | Variable | Unused in JobContext |

**Note:** `src/alfred/cron/protocol.py` is part of active PRD #120 (Cron Job Linter and Socket API) and should NOT be removed.

#### Memory System

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/memory/base.py:53` | `delete` | Method | Abstract method never implemented |
| `src/alfred/memory/sqlite_store.py:205` | `prune_expired_memories` | Method | Never called |
| `src/alfred/memory/sqlite_store.py:254` | `delete_entries` | Method | Never called |
| `src/alfred/memory/sqlite_store.py:282` | `check_memory_threshold` | Method | Never called |

#### CLI and Interface

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/cli/main.py:93-302` | Multiple cron/memory CLI functions | Functions | All defined but unused by Typer |
| `src/alfred/container.py:56` | `has` | Method | Never called |
| `src/alfred/interfaces/ansi.py:76-80` | `ITALIC`, `UNDERLINE`, `BLINK`, `STRIKE` | Variables | Unused ANSI codes |
| `src/alfred/interfaces/ansi.py:88` | `WHITE` | Variable | Unused color constant |
| `src/alfred/interfaces/notification_buffer.py:22` | `NotificationBuffer` | Class | Complete class unused |
| `src/alfred/interfaces/notification_buffer.py:56` | `set_active` | Method | Never called |
| `src/alfred/interfaces/notification_buffer.py:87` | `pending_count` | Property | Never accessed |
| `src/alfred/interfaces/status.py:45` | `StatusRenderer` | Class | Complete class unused |
| `src/alfred/interfaces/status.py:60` | `to_prompt_toolkit` | Method | Never called |

#### TUI Components

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/interfaces/pypitui/completion_addon.py:45` | `_active_trigger` | Attribute | Never read |
| `src/alfred/interfaces/pypitui/completion_addon.py:231` | `check_pending_update` | Method | Never called |
| `src/alfred/interfaces/pypitui/completion_menu_component.py:15` | `ANSI_ESCAPE` | Variable | Unused regex |
| `src/alfred/interfaces/pypitui/completion_menu_component.py:25` | `is_static` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/message_panel.py:47` | `_role` | Attribute | Never read |
| `src/alfred/interfaces/pypitui/message_panel.py:50` | `_border_color` | Attribute | Never read |
| `src/alfred/interfaces/pypitui/message_panel.py:170` | `get_tool_call` | Method | Never called |
| `src/alfred/interfaces/pypitui/message_panel.py:361` | `_content` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/status_line.py:12` | `STATUS_WIDTH_COMPACT` | Variable | Unused constant |
| `src/alfred/interfaces/pypitui/status_line.py:44` | `is_static` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/throbber.py:431` | `frame_count` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/throbber.py:436` | `current_index` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/throbber.py:442` | `list_throbber_styles` | Function | Never called |
| `src/alfred/interfaces/pypitui/toast.py:136` | `get_toasts` | Function | Never called |
| `src/alfred/interfaces/pypitui/tui.py:67` | `_scrollback_position` | Attribute | Never read |
| `src/alfred/interfaces/pypitui/tui.py:158` | `_reset_ctrl_c_state` | Method | Never called |
| `src/alfred/interfaces/pypitui/tui.py:165` | `_update_toast_overlay` | Method | Never called |
| `src/alfred/interfaces/pypitui/tui.py:214` | `_on_resize` | Method | Never called |
| `src/alfred/interfaces/pypitui/wrapped_input.py:46` | `is_static` | Property | Never accessed |
| `src/alfred/interfaces/pypitui/wrapped_input.py:83` | `add_render_hook` | Method | Never called |
| `src/alfred/interfaces/pypitui/wrapped_input.py:104` | `with_completion_component` | Method | Never called |

#### Tools

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/tools/__init__.py:73` | `clear_registry` | Function | Never called |
| `src/alfred/tools/__init__.py:80` | `get_tool_schemas` | Function | Never called |
| `src/alfred/tools/approve_job.py:23` | `validate_identifier` | Method | Never called |
| `src/alfred/tools/base.py:135` | `validate_and_run` | Method | Never called |
| `src/alfred/tools/list_jobs.py:24` | `ListJobsResult` | Class | Unused result class |
| `src/alfred/tools/mixins.py:22` | `_require_memory_store` | Method | Never called |
| `src/alfred/tools/mixins.py:35` | `_handle_error` | Method | Never called |
| `src/alfred/tools/mixins.py:42` | `_format_success` | Method | Never called |
| `src/alfred/tools/reject_job.py:23` | `validate_identifier` | Method | Never called |
| `src/alfred/tools/schedule_job.py:45` | `validate_name` | Method | Never called |
| `src/alfred/tools/schedule_job.py:53` | `validate_description` | Method | Never called |
| `src/alfred/tools/search_sessions.py:30` | `serialize_datetime` | Method | Never called |
| `src/alfred/tools/search_sessions.py:132` | `load_summary` | Method | Never called |
| `src/alfred/tools/search_sessions.py:190` | `_find_relevant_sessions` | Method | Never called |
| `src/alfred/tools/search_sessions.py:212` | `_search_session_messages` | Method | Never called |

#### Session Management

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/session.py:72-74` | `first_message_time`, `last_summarized_count`, `summary_version` | Variables | Unused in SessionMeta |
| `src/alfred/session.py:292` | `resume_session` | Method | Never called |
| `src/alfred/session.py:508` | `clear_session` | Method | Never called |
| `src/alfred/session_context.py:10` | `SessionContextBuilder` | Class | Complete class unused |

#### Storage

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/storage/sqlite.py:399` | `delete_session` | Method | Never called |
| `src/alfred/storage/sqlite.py:539` | `get_job_history` | Method | Never called |
| `src/alfred/storage/sqlite.py:1083` | `find_sessions_needing_summary` | Method | Never called |

#### Other

| File | Line | Name | Type | Issue |
|------|------|------|------|-------|
| `src/alfred/placeholders.py:19` | `CircularReferenceError` | Class | Exception unused |
| `src/alfred/placeholders.py:291` | `resolve_file_includes` | Function | Never called |
| `src/alfred/placeholders.py:310` | `resolve_colors` | Function | Never called |
| `src/alfred/templates.py:234` | `ensure_all_exist` | Method | Never called |
| `src/alfred/templates.py:250` | `list_templates` | Method | Never called |
| `src/alfred/templates.py:266` | `list_missing` | Method | Never called |
| `src/alfred/type_defs.py:12` | `ensure_json_object` | Function | Never called |
| `src/alfred/llm.py:117` | `retry_with_backoff` | Function | Decorator unused |
| `src/alfred/llm.py:156` | `stream_chat` | Method | Never called |
| `src/alfred/llm.py:161` | `chat_with_tools` | Method | Never called |
| `src/alfred/llm.py:242` | `chat_with_tools` | Method | Never called |
| `src/alfred/llm.py:303` | `stream_chat` | Method | Never called |

### Configuration Dead Code

| File | Lines | Variables | Issue |
|------|-------|-----------|-------|
| `src/alfred/config.py` | 46-47 | `memory_ttl_days`, `memory_warning_threshold` | Config fields unused |
| `src/alfred/config.py` | 59-61 | `faiss_index_type`, `faiss_ivf_threshold`, `faiss_backup_jsonl` | FAISS config unused (FAISS removed) |

### Job Linter Dead Code

| File | Lines | Variables | Issue |
|------|-------|-----------|-------|
| `src/alfred/cron/job_linter.py` | 110-111, 130, 138 | `found_notify_call`, `found_subprocess_notify` | Attributes set but never read |

---

## Poor Quality Tests

### Skipped Tests (6 found)

| File | Line | Test Name | Skip Reason |
|------|------|-----------|-------------|
| `tests/test_session_cli.py:191` | `test_chat_stream_adds_user_message` | "Integration test - requires full Alfred mock setup" |
| `tests/test_session_cli.py:197` | `test_chat_stream_adds_assistant_response` | "Integration test - requires full Alfred mock setup" |
| `tests/test_integration.py:304` | `test_all_tools_registered` | `skipif` condition |
| `tests/pypitui/test_notifier_toast.py:40` | `test_cli_notifier_with_buffer` | "Pre-existing failure: AlfredTUI doesn't set toast_manager on notifier" |
| `tests/tools/test_update_memory.py:74` | Test method | "Importance field removed from MemoryEntry" |
| `tests/embeddings/test_provider.py` | Multiple tests | `skipif` for optional dependencies |

### Empty or Near-Empty Tests

| File | Line | Test | Issue |
|------|------|------|-------|
| `tests/test_session_cli.py:193` | `test_chat_stream_adds_user_message` | Body is just `pass` |
| `tests/test_session_cli.py:199` | `test_chat_stream_adds_assistant_response` | Body is just `pass` |
| `tests/test_session.py:77` | `spawn_embed_task` | Method body is `pass # No-op in mock` |
| `tests/pypitui/test_ansi.py:250` | Test method | `pass  # TODO: Verify actual behavior after running test` |

### Tests with Poor Assertions

| File | Line | Issue |
|------|------|-------|
| `tests/test_session_cli.py` | Uses MockStorage that doesn't actually persist | Tests don't verify real SQLite behavior |
| `tests/tools/test_schedule_job.py` | Multiple `pass` statements | Empty test implementations |
| `tests/tools/test_schedule_job_integration.py` | Multiple `pass` statements | Empty integration test methods |
| `tests/tools/test_forget.py` | Multiple `pass` statements | Empty test implementations |

---

## Empty/Minimal Files (10 found)

These files have 4 or fewer lines of actual code:

| File | Lines | Issue |
|------|-------|-------|
| `tests/__init__.py` | 0 | Completely empty |
| `src/alfred/cli/__init__.py` | 1 | Empty init file |
| `tests/pypitui/__init__.py` | 1 | Empty init file |
| `tests/embeddings/__init__.py` | 1 | Empty init file |
| `src/alfred/interfaces/__init__.py` | 1 | Empty init file |
| `src/alfred/utils/__init__.py` | 3 | Minimal init file |
| `src/alfred/storage/__init__.py` | 3 | Minimal init file |
| `src/alfred/__init__.py` | 4 | Only version info |
| `src/alfred/interfaces/pypitui/constants.py` | 4 | Only constants, not used elsewhere |
| `tests/e2e/__init__.py` | 4 | Near-empty init file |

---

## Model Configuration Boilerplate

Multiple files have unused `model_config` variables:

| File | Line | Context |
|------|------|---------|
| `src/alfred/config.py:21` | Pydantic config variable |
| `src/alfred/context.py:40` | Pydantic model config |
| `src/alfred/tools/base.py:15` | Tool params model config |
| `src/alfred/tools/base.py:21` | Tool params model config |
| `src/alfred/tools/search_memories.py:15` | Search params model config |
| `src/alfred/tools/search_sessions.py:38` | Search params model config |
| `src/alfred/tools/update_memory.py:14` | Update params model config |

---

## Duplicate Code Patterns

### Similar Method Pairs (Could be consolidated)

| File | Methods | Issue |
|------|---------|-------|
| `src/alfred/session.py` | `get_or_create_session` / `get_or_create_session_async` | Near-duplicate sync/async versions |
| `src/alfred/session.py` | `list_sessions` / `list_sessions_async` | Near-duplicate sync/async versions |
| `src/alfred/session.py` | `session_exists` / `session_exists_async` | Near-duplicate sync/async versions |
| `src/alfred/session.py` | `resume_session` / `resume_session_async` | Near-duplicate sync/async versions |
| `src/alfred/llm.py` | Multiple `stream_chat` / `chat_with_tools` methods | Interface duplication |

---

## Recommendations

### Immediate Cleanup (High Priority)

1. **Remove completely unused classes:**
   - `NaturalLanguageCronParser`
   - `CLINotifier`
   - `TelegramNotifier`
   - `NotificationBuffer`
   - `SessionContextBuilder`
   - `StatusRenderer`

2. **Remove empty test methods** or implement them

3. **Remove FAISS-related config** (FAISS was removed in PRD #109)

### Medium Priority

1. Consolidate sync/async method pairs using a wrapper pattern
2. Clean up unused imports
3. Review PRD #120 protocol code after implementation is complete

### Exclusions - DO NOT REMOVE

The following files are part of **active PRD #120** (Cron Job Linter and Socket API) and should NOT be removed:
- `src/alfred/cron/protocol.py` - Socket protocol definitions (in progress)
- `src/alfred/cron/socket_client.py` - Socket client (in progress)  
- `src/alfred/cron/socket_server.py` - Socket server (in progress)
- `src/alfred/cron/job_linter.py` - Job linter (mostly complete)

### Low Priority

1. Remove empty `__init__.py` files or add useful exports
2. Clean up unused ANSI color codes
3. Remove unused model_config boilerplate

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Unused classes | 15+ |
| Unused methods/functions | 60+ |
| Unused variables/attributes | 40+ |
| Skipped tests | 6 |
| Empty tests | 5+ |
| Empty/minimal files | 10 |
| **Total Issues** | **120+** |

---

*Note: Analysis performed using vulture with 60% confidence threshold and manual code review.*
