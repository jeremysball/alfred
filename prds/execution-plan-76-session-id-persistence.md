# Execution Plan: PRD 76 Session ID Persistence

- [x] Create `tests/test_session_id_persistence.py` with new TDD coverage:
  - [x] Test: `test_session_manager_assigns_session_id()` — message in session has session_id set
  - [x] Test: `test_storage_persists_session_id()` — current.jsonl line includes session_id
  - [x] Test: `test_load_messages_requires_session_id()` — missing session_id raises ValueError
- [x] Run: `uv run pytest tests/test_session_id_persistence.py -v` (expect failures)
- [x] Update `src/session.py`:
  - [x] Set `Message.session_id` in `SessionManager.add_message()`
- [x] Update `src/session_storage.py`:
  - [x] Persist `session_id` in `append_message()`
  - [x] Require/validate `session_id` in `load_messages()`
  - [x] Persist `session_id` when rewriting in `update_message_embedding()`
- [x] Update existing tests to include required `session_id` field (e.g., `tests/test_session_storage.py`)
- [x] Run: `uv run pytest tests/test_session_id_persistence.py -v`
- [x] Run: `uv run pytest tests/test_session_storage.py -v`
- [x] Run: `uv run ruff check src/ && uv run mypy src/ && uv run pytest`
