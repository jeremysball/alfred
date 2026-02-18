# PRD: Fix Kimi reasoning_content Extraction from Streaming Delta

## Issue
#40

## Status
In Progress

## Priority
High

## Problem Statement

Kimi API with thinking mode enabled requires `reasoning_content` to be present in assistant messages that have tool calls. Currently, `stream_chat_with_tools()` does not extract `reasoning_content` from the streaming response delta chunks. This causes API errors:

```
Error code: 400 - {'error': {'message': 'thinking is enabled but reasoning_content 
is missing in assistant tool call message at index 1', 'type': 'invalid_request_error'}}
```

## Root Cause

In `KimiProvider.stream_chat_with_tools()`, the code extracts:
- `delta.content` ✓
- `delta.tool_calls` ✓
- `delta.reasoning_content` ✗ (missing!)

When the agent constructs the assistant message with tool calls, it checks for `reasoning_content` but this was never populated because the streaming method didn't extract it from the delta.

## Solution Overview

Modify `stream_chat_with_tools()` to:
1. Extract `delta.reasoning_content` from each streaming chunk
2. Accumulate reasoning content across chunks
3. Include `reasoning_content` in the assistant message when tool calls are present

## Technical Details

### Current Flow (Broken)
```
Stream chunks → extract content + tool_calls
                ↓
        Assistant message created
                ↓
        NO reasoning_content
                ↓
        Next API call FAILS
```

### Fixed Flow
```
Stream chunks → extract content + tool_calls + reasoning_content
                ↓
        Assistant message with reasoning_content
                ↓
        Next API call SUCCEEDS
```

## Implementation Plan

### Milestone 1: Fix reasoning_content Extraction
- [x] Modify `stream_chat_with_tools()` to extract `delta.reasoning_content`
- [x] Accumulate reasoning content across streaming chunks
- [x] Ensure reasoning_content is passed through in assistant messages with tool calls
- [ ] Verify fix with manual test

### Milestone 2: Testing Strategy Evaluation
- [ ] Evaluate current test coverage for streaming with tool calls
- [ ] Determine if new tests are needed for reasoning_content
- [ ] Document testing approach decision

### Milestone 3: Regression Testing
- [ ] Run full test suite
- [ ] Verify no existing functionality broken
- [ ] Verify integration tests pass

## Success Criteria
- [ ] Tool calls work with Kimi API when thinking mode is enabled
- [ ] `stream_chat_with_tools()` correctly extracts and propagates reasoning_content
- [ ] All tests pass
- [ ] Integration tests with real LLM pass

## Testing Strategy Decision

**Decision**: Option B - Rely on integration tests, document the requirement

**Rationale**:
- This is provider-specific behavior (Kimi thinking mode) that doesn't generalize to other providers
- Unit tests would require complex mocking of streaming deltas with reasoning_content
- Integration tests with real API properly validate the full flow
- Documented requirement in code comments will guide future maintainers

**Action Items**:
- [x] Add code comment in `stream_chat_with_tools()` documenting reasoning_content extraction requirement
- [ ] Ensure integration tests cover tool calls with streaming

## Related Code
- `src/llm.py` - `KimiProvider.stream_chat_with_tools()`
- `src/agent.py` - Agent loop that constructs assistant messages

## Dependencies
- None (self-contained fix)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | PRD Created | Fix required for Kimi tool calls with thinking mode |
| 2026-02-18 | Testing Strategy: Option B | Rely on integration tests, document requirement - provider-specific behavior not suited for unit tests |
