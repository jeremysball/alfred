# Execution Plan: PRD #147 - Milestone 4: Inject Self-Model into Context Assembly

## Overview
Integrate the self-model into Alfred's context assembly pipeline so the LLM receives runtime self-awareness with every prompt.

---

## Milestone 4: Inject the self-model into context assembly

### Component: Extend AssembledContext model

- [x] **Test**: Verify `AssembledContext` can hold `self_model` field
- [x] **Implement**: Add `self_model: RuntimeSelfModel | None = None` to `AssembledContext`
- [x] **Run**: `uv run pytest tests/test_self_model.py -v`

### Component: Add self-model serialization

- [x] **Test**: `test_runtime_self_model_to_prompt_section()` - verify markdown output format
- [x] **Implement**: Add `to_prompt_section()` method to `RuntimeSelfModel`
- [x] **Run**: `uv run pytest tests/test_self_model.py::test_runtime_self_model_to_prompt_section -v`

### Component: ContextLoader integration

- [x] **Test**: Verify `assemble_with_self_model()` returns context with self-model
- [x] **Implement**: Add `assemble_with_self_model(alfred)` method to `ContextLoader`
- [x] **Implement**: Update `assemble_with_search()` to accept optional `alfred` parameter
- [x] **Run**: Verify integration with existing tests

### Component: Alfred integration

- [x] **Implement**: Update Alfred to use `assemble_with_self_model(self)` in message processing
- [x] **Implement**: Pass `alfred=self` to `assemble_with_search()` calls
- [x] **Run**: `uv run pytest tests/test_self_model.py -v`

---

## Files Modified

1. `src/alfred/context.py` — Extended `AssembledContext`, added `assemble_with_self_model()`, updated `assemble_with_search()`
2. `src/alfred/self_model.py` — Added `to_prompt_section()` method
3. `src/alfred/alfred.py` — Updated to use new assembly methods
4. `tests/test_self_model.py` — Added serialization tests

---

## Exit Criteria for Milestone 4

- Self-model appears in assembled context on every turn
- Prompt includes compact markdown representation of Alfred's state
- Internal visibility flag prevents user exposure
- All existing tests pass
- Ready for Milestone 5: Surface `/context` summary
