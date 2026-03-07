# Execution Plan: PRD #76 - Record Store Backend Refactor

- [ ] Create `src/storage/__init__.py`
- [ ] Create `src/storage/record_store.py` with `RecordStore` interface and `JsonlRecordStore`
- [ ] Add tests in `tests/storage/test_record_store.py` for append/read/rewrite
- [ ] Run: `uv run pytest tests/storage/test_record_store.py -v` (expect fail)
- [ ] Update `src/memory/jsonl_store.py` to use `JsonlRecordStore`
- [ ] Update `src/session_storage.py` to use `JsonlRecordStore`
- [ ] Run: `uv run pytest tests/storage/test_record_store.py -v`
- [ ] Run: `uv run ruff check src/`
- [ ] Run: `uv run mypy src/`
- [ ] Run: `uv run pytest`
