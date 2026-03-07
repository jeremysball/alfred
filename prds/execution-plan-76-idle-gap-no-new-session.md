# Execution Plan: PRD #76 - Idle Gap No New Session

- [ ] Update `tests/test_session.py` to assert idle gaps do not create new sessions
- [ ] Run: `uv run pytest tests/test_session.py -v` (expect fail)
- [ ] Update `src/session.py` to keep current session after idle gap
- [ ] Run: `uv run pytest tests/test_session.py -v`
- [ ] Run: `uv run ruff check src/` and `uv run mypy src/`
- [ ] Run: `uv run pytest`
