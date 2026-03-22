# Execution Plan: PRD #144 - Milestone 7

## Overview

Close out the observability work with documentation, regression coverage, and full verification. The implementation should already be clear enough to use; this phase makes that clarity durable by documenting the commands, the surfaces, and the expected debugging workflow.

**Current Phase:** Milestone 7 - Documentation and final verification

---

## Milestone 7: Documentation and final verification

### 7.1 README documents surface-scoped logging

- [ ] **Test**: `test_readme_documents_surface_scoped_logging()`
  - Keep `tests/test_readme_logging.py` aligned with the final README copy
  - Assert the README explains root vs Web UI logging scopes and the surface labels developers should expect
- [ ] **Implement**: update `README.md`
  - Document `alfred --log debug`, `alfred webui --log debug`, and combined usage
  - Include the relevant surface names and a concise explanation of what each one means
  - Keep the examples grep-friendly and easy to skim
- [ ] **Run**: `uv run pytest tests/test_readme_logging.py -v`

### 7.2 Verification sweep catches regressions before closeout

- [ ] **Test**: run the targeted regression set for the new observability surfaces
  - Use the logging, storage, LLM, core, and Web UI tests that cover the new behavior
- [ ] **Implement**: fix any mismatches surfaced by the regression sweep
  - Keep the fix set small and aligned with the observed failure
- [ ] **Run**: `uv run pytest tests/test_cli_webui_logging.py tests/test_observability.py tests/test_core_observability.py tests/test_llm_observability.py tests/test_readme_logging.py tests/storage/test_storage_observability.py tests/webui/test_frontend_logging.py -q`

### 7.3 Runtime startup still works with the finished observability model

- [ ] **Test**: `test_webui_and_tui_startup_still_work_with_surface_logging()`
  - Confirm the actual application launches after the observability changes
  - Include the TUI or Web UI entry point that best matches the final touched surface
- [ ] **Implement**: patch any startup regression uncovered during the smoke test
  - Keep launch behavior intact while preserving the new logging surfaces
- [ ] **Run**: `uv run alfred --log debug`

---

## Files to Modify

1. `README.md` - final logging and debugging guidance
2. `tests/test_readme_logging.py` - documentation regression coverage
3. `tests/test_cli_webui_logging.py` - final logging-control regression sweep if needed
4. `tests/test_observability.py` - final surface-format regression sweep if needed
5. `tests/test_core_observability.py` - final runtime logging regression sweep if needed
6. `tests/test_llm_observability.py` - final LLM logging regression sweep if needed
7. `tests/storage/test_storage_observability.py` - final storage logging regression sweep if needed
8. `tests/webui/test_frontend_logging.py` - final Web UI client logging regression sweep if needed

## Verification Commands

```bash
uv run pytest tests/test_readme_logging.py tests/test_cli_webui_logging.py tests/test_observability.py tests/test_core_observability.py tests/test_llm_observability.py tests/storage/test_storage_observability.py tests/webui/test_frontend_logging.py -q
uv run ruff check src/ tests/
uv run mypy --strict src/
uv run pytest -m "not slow"
uv run alfred --log debug
uv run alfred webui --port 8080
uv run alfred --log debug webui --log debug
```

## Commit Strategy

Suggested atomic commits:
- `docs(readme): document surface-scoped logging`
- `test(observability): cover final logging and docs regressions`
- `chore(verification): run final observability sweep`

## Next Task

- [ ] **Test**: `test_readme_documents_surface_scoped_logging()`
- [ ] **Implement**: update `README.md`
- [ ] **Run**: `uv run pytest tests/test_readme_logging.py -v`
