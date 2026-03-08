# PRD: Evaluate and Improve Testing Strategy

## Issue
#41

## Status
Ready for Implementation - Requirements Gathered

## Priority
High

## Problem Statement

Our current testing strategy has significant gaps that allow bugs to reach production. Recent examples:

1. **reasoning_content bug** (#40): Streaming delta extraction was broken but all unit tests passed
2. **CLI test failures**: Tests mocked wrong methods (`chat` instead of `chat_stream`)
3. **Integration test brittleness**: Real API tests fail unpredictably due to provider changes
4. **Async mocking complexity**: Async generators are hard to mock correctly

## Current State Analysis

### What We Have
- 232+ unit tests with mocks
- Integration tests that require real API keys
- Heavy use of `unittest.mock.AsyncMock` and `MagicMock`
- Tests for individual components but not full flows

### What's Working
- Fast test execution (~10s for full suite)
- Good coverage of happy paths
- CI-friendly (no external dependencies)

### What's Broken
- **False confidence**: Unit tests pass but real behavior broken
- **Mock drift**: Tests mock implementation details, not behavior
- **Integration gaps**: Critical paths only tested with real APIs
- **Maintenance burden**: Changing implementation breaks tests unnecessarily

## Requirements Gathering - COMPLETED

### Question 1: Pain Points ✅
**Answer: D - Can't trust test results, manually verify everything**

Current unit tests give false confidence. When you see green tests, you still don't know if the code actually works.

### Question 2: Ideal State ✅
**Answer: Tests as guardrails to keep honest and stress test assumptions**

Tests should catch when reality diverges from assumptions. Integration tests are the guardrails that prevent shipping broken code.

### Question 3: Bug Patterns ✅
**Answer: B and C - API provider changes and Tool execution edge cases**

- API provider behavior changes (e.g., Kimi reasoning_content requirement)
- Tool execution not working as expected in real flows

### Question 4: Speed vs Coverage ✅
**Answer: Verifying behavior is utmost importance. Integration tests keep us honest.**

Speed is secondary to correctness. Full suite doesn't need to run often, but when it does, it should catch real issues.

### Question 5: Test Philosophy ✅
**Answer: Both - Any bugs need regression testing, but verifying behavior is utmost importance**

Tests must:
1. Verify behavior works as intended (primary)
2. Prevent known bugs from recurring (secondary)

## Recommended Strategy: Integration-First with Recording

Based on your answers, the best approach is **Strategy C (Recording/Playback)** with **Strategy B (Layered Pyramid)** for organization.

### Why This Strategy Fits Your Needs

| Your Need | How This Strategy Delivers |
|-----------|---------------------------|
| Can't trust current tests | Recording captures REAL behavior, not mocked assumptions |
| Guardrails to keep honest | Integration tests verify against actual API behavior |
| Catch API provider changes | Recordings detect when provider responses change |
| Tool execution edge cases | Full flow tests exercise real tool execution |
| Verify behavior is primary | Tests verify actual behavior, not implementation |
| Don't run full suite often | Fast playback mode for daily dev, record mode on demand |

### The Three Layers

#### Layer 1: Unit Tests (Fast, Playback Mode)
- Uses recorded API responses
- Run on every commit
- < 10 seconds
- Catches regressions in business logic

#### Layer 2: Integration Tests (Real APIs, Record Mode)
- Hits real APIs, updates recordings
- Run before merging PRs
- 30-60 seconds
- Catches API changes, verifies behavior

#### Layer 3: Full System Tests (E2E)
- Complete user flows
- Run nightly or on release
- Validates entire system works together

### Example: Recording/Playback Test

```python
# tests/test_llm_recording.py
@pytest.mark.vcr(record_mode="none")  # Use existing recording
def test_stream_chat_with_tools_reasoning():
    """Test extracted from reasoning_content bug (#40).
    
    Recording captured real Kimi API response with reasoning_content.
    If Kimi changes their API, this test will fail and we re-record.
    """
    provider = KimiProvider(config)
    messages = [ChatMessage(role="user", content="Use a tool")]
    
    chunks = list(provider.stream_chat_with_tools(messages, tools=schemas))
    
    # Verify behavior: reasoning_content extracted and yielded
    assert any(c.startswith("[REASONING]") for c in chunks)
    assert any(c.startswith("[TOOL_CALLS]") for c in chunks)

@pytest.mark.vcr(record_mode="once")  # Record if no cassette exists
def test_stream_chat_records_new_behavior():
    """When adding new features, run in record mode once."""
    # ... test with real API, creates recording for future runs
```

### Benefits

1. **Trustworthy**: Tests verify real behavior, not mocked assumptions
2. **Fast Feedback**: Playback mode is instant
3. **Honest Guardrails**: Record mode catches API drift
4. **Maintainable**: No complex mocking of async generators
5. **Regression Prevention**: Recordings are the spec - if they change, behavior changed

### Tradeoffs

- **Requires VCR library** (pytest-recording or similar)
- **Recordings are large** (API responses stored as files)
- **API calls cost money** when recording
- **Sensitive data** in recordings (need sanitization)

## Implementation Plan

### Milestone 1: Setup Recording Infrastructure
- [ ] Add `pytest-recording` or `vcrpy` to dependencies
- [ ] Configure cassette storage (tests/cassettes/)
- [ ] Set up cassette sanitization for API keys
- [ ] Create pytest markers for recording modes

### Milestone 2: Migrate Critical Tests to Recording
- [ ] Convert LLM provider tests (stream_chat, stream_chat_with_tools)
- [ ] Convert agent loop tests (tool execution flow)
- [ ] Convert tool execution tests (bash, read, write)
- [ ] Record cassettes for each provider (Kimi, future providers)

### Milestone 3: Remove Brittle Mocks
- [ ] Identify tests that mock async generators
- [ ] Replace with recording-based tests
- [ ] Delete mock-based tests that test implementation details
- [ ] Verify coverage doesn't drop

### Milestone 4: Documentation & Workflow
- [ ] Document when to run in record mode vs playback mode
- [ ] Add CI workflow for nightly recording refresh
- [ ] Create playbook for "recording changed, investigate"
- [ ] Update PR template to remind about recordings

### Milestone 5: Bug Regression Tests
- [ ] Create recording test for #40 (reasoning_content)
- [ ] Create recording test for CLI streaming
- [ ] Document pattern: "For each bug fix, add recording test"

## Success Criteria
- [ ] Can run full test suite in < 10 seconds (playback mode)
- [ ] Can run with real APIs to refresh recordings (record mode)
- [ ] reasoning_content bug would have been caught by recording
- [ ] Tool execution edge cases tested with real API responses
- [ ] API provider changes detected automatically when recordings differ
- [ ] Team trusts test results (no more manual verification)

## Related Issues
- #40 - reasoning_content bug that slipped through testing

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | PRD Created | Testing strategy evaluation initiated |
| 2026-02-18 | Requirements Gathered | Pain point: Can't trust tests (D). Goal: Guardrails/honesty. Bugs: API changes + tool execution. Philosophy: Behavior verification + regression prevention. |
| 2026-02-18 | Strategy Selected | Integration-First with Recording/Playback. Captures real API behavior, catches provider changes, maintains fast playback mode for daily dev. |
