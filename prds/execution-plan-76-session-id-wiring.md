# Execution Plan: PRD #76 - Session ID Wiring

- [ ] Create `tests/integration/test_session_id_wiring.py`
- [ ] Add test `test_message_written_gets_session_id()` to verify persisted JSON includes `session_id`
- [ ] Run: `uv run pytest tests/integration/test_session_id_wiring.py -v` (expect fail)
- [ ] Update `src/session.py` to set `Message.session_id` in `SessionManager.add_message()` using `assign_session_id`
- [ ] Update `src/session_storage.py` to persist `session_id` in `append_message()`
- [ ] Update `src/session_storage.py` to load/validate `session_id` in `load_messages()`
- [ ] Run: `uv run pytest tests/integration/test_session_id_wiring.py -v`
- [ ] Run: `uv run pytest tests/test_session_id_persistence.py -v`
- [ ] Run: `uv run ruff check src/` and `uv run mypy src/`
- [ ] Run: `uv run pytest`
