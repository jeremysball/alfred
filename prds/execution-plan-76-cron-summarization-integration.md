# Execution Plan: PRD #76 - Cron Summarization Integration Test

- [ ] Create `tests/integration/test_session_summarization_cron.py`
- [ ] Add slow integration test `test_cron_finds_and_summarizes_idle_session()`
- [ ] Run: `uv run pytest tests/integration/test_session_summarization_cron.py -v -m "slow and integration"`
- [ ] Run: `uv run ruff check src/`
- [ ] Run: `uv run mypy src/`
- [ ] Run: `uv run pytest`
