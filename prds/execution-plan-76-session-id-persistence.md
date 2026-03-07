# Execution Plan: PRD 76 Session ID Persistence

- [ ] Create `tests/test_session_id_persistence.py` with new TDD coverage:
  - [ ] Test: `test_session_manager_assigns_session_id()` — message in session has session_id set
  - [ ] Test: `test_storage_persists_session_id()` — current.jsonl line includes session_id
  - [ ] Test: `test_load_messages_requires_session_id()` — missing session_id raises ValueError
- [ ] Run: `uv run pytest tests/test_session_id_persistence.py -v` (expect failures)
- [ ] Update `src/session.py`:
  - [ ] Set `Message.session_id` in `SessionManager.add_message()`
- [ ] Update `src/session_storage.py`:
  - [ ] Persist `session_id` in `append_message()`
  - [ ] Require/validate `session_id` in `load_messages()`
  - [ ] Persist `session_id` when rewriting in `update_message_embedding()`
- [ ] Update existing tests to include required `session_id` field (e.g., `tests/test_session_storage.py`)
- [ ] Run: `uv run pytest tests/test_session_id_persistence.py -v`
- [ ] Run: `uv run pytest tests/test_session_storage.py -v`
- [ ] Run: `uv run ruff check src/ && uv run mypy src/ && uv run pytest`
