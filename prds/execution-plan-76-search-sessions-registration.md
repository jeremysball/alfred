# Execution Plan: PRD 76 SearchSessionsTool Registration (Option B)

- [ ] Create file `tests/tools/test_search_sessions.py` test: missing dependencies returns JSON error
- [ ] Update `tests/test_integration.py` to expect `search_sessions` in registry when dependencies missing
- [ ] Update `tests/test_integration.py` schema count to include `search_sessions`
- [ ] Run: `uv run pytest tests/tools/test_search_sessions.py -v` (expect failure)
- [ ] Run: `uv run pytest tests/test_integration.py::TestToolRegistryIntegration -v` (expect failure)
- [ ] Update `src/tools/search_sessions.py` to accept optional `storage`/`embedder`
- [ ] Add dependency check in `SearchSessionsTool.execute_stream()` to return JSON error
- [ ] Update `src/tools/__init__.py` to always register `SearchSessionsTool`
- [ ] Remove `llm_client` argument from `SearchSessionsTool` construction
- [ ] Run: `uv run pytest tests/tools/test_search_sessions.py -v`
- [ ] Run: `uv run pytest tests/test_integration.py::TestToolRegistryIntegration -v`
- [ ] Run: `uv run ruff check src/`
- [ ] Run: `uv run basedpyright src/`
- [ ] Run: `uv run pytest`
