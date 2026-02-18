# PRD: Implement VCR-Based Testing with Pre-PR Recording Checks

## Issue
#42

## Status
Ready for Implementation

## Priority
High

## Problem Statement

Our current testing strategy relies heavily on mocks, which creates a false sense of security:

1. **Unit tests pass but real behavior is broken** - The `reasoning_content` bug (#40) passed all tests
2. **Async generator mocking is complex and error-prone** - Tests break when implementation details change
3. **Can't trust test results** - We manually verify everything anyway
4. **API provider changes go undetected** - Kimi added thinking mode requirement, we didn't catch it

We need tests that act as **guardrails to keep us honest** and **stress test our assumptions** against reality.

## Solution Overview

Implement **VCR-based testing** using `pytest-recording` (or `vcrpy`):

- **Daily Development**: Fast playback mode using recorded API responses (<10s)
- **Pre-PR Merge**: Re-record with real APIs to detect provider changes
- **Workflow**: Fail CI if recordings change unexpectedly (requires human review)

### Why pytest-recording Over vcrpy

| Feature | pytest-recording | vcrpy |
|---------|------------------|-------|
| Pytest integration | Native decorators | Manual fixture setup |
| Cassette management | Automatic per-test | Manual configuration |
| Async support | Built-in | Requires extra setup |
| Sanitization | Easy config | More verbose |
| Maintenance | Active | Stable but slower updates |

**Decision**: `pytest-recording` - better pytest integration, less boilerplate.

## Technical Architecture

### Cassette Structure

```
tests/
├── cassettes/
│   ├── test_llm/
│   │   ├── test_stream_chat.yaml
│   │   └── test_stream_chat_with_tools.yaml
│   ├── test_agent/
│   │   └── test_tool_execution_flow.yaml
│   └── test_tools/
│       └── test_bash_execution.yaml
└── conftest.py  # VCR configuration
```

### Workflow: Option C (Pre-PR Recording Checks)

```
Daily Development:
  $ pytest tests/           # Playback mode - uses cassettes (<10s)

Before PR Merge:
  $ just check-recordings   # Re-record + verify no unexpected changes
  
  Steps:
  1. Run tests with VCR_RECORD_MODE=rewrite
  2. Compare cassettes to baseline
  3. If changed: fail with message "API behavior changed - review needed"
  4. If review approves: commit cassettes with PR

CI Pipeline:
  - On PR: Fast playback mode only
  - On merge to main: Optional re-record + auto-commit if clean
```

### Sanitization Requirements

Cassettes MUST sanitize:
- API keys (Authorization headers)
- Tokens in query params
- Sensitive user data in request/response bodies

## Implementation Plan

### Milestone 1: Infrastructure Setup
**Goal**: Install and configure pytest-recording

- [ ] Add `pytest-recording` to dev dependencies
- [ ] Create `tests/conftest.py` with VCR configuration
- [ ] Set up cassette storage structure (`tests/cassettes/`)
- [ ] Configure sanitization for API keys
- [ ] Add `VCR_RECORD_MODE` environment variable handling
- [ ] Create `justfile` commands for recording workflow

**Success Criteria**:
- `pytest tests/` runs in playback mode by default
- `just check-recordings` command exists
- API keys are sanitized in cassettes

### Milestone 2: Create Initial Cassettes
**Goal**: Record real API interactions for critical paths

- [ ] Create cassette for `stream_chat` (Kimi provider)
- [ ] Create cassette for `stream_chat_with_tools` with reasoning_content
- [ ] Create cassette for agent tool execution flow
- [ ] Create cassette for bash tool execution
- [ ] Create cassette for read/write tool execution
- [ ] Verify all cassettes are sanitized

**Success Criteria**:
- 5+ cassettes covering core LLM and tool flows
- All cassettes committed to repo
- Tests pass in playback mode

### Milestone 3: Migrate Critical Tests
**Goal**: Replace mock-based tests with recording-based tests

- [ ] Migrate `test_llm.py` - use recordings instead of mocks
- [ ] Migrate `test_agent.py` - test real agent flows
- [ ] Migrate `test_tools/` - test real tool execution
- [ ] Delete brittle mock-based tests
- [ ] Ensure coverage doesn't drop below 80%

**Success Criteria**:
- No async generator mocking in test suite
- All critical paths tested with recordings
- Coverage ≥ 80%

### Milestone 4: Pre-PR Check Workflow
**Goal**: Implement Option C workflow in CI

- [ ] Add `just check-recordings` command
- [ ] Add GitHub Actions workflow for PR recording check
- [ ] Create PR template section for recordings
- [ ] Document "when to re-record" guidelines
- [ ] Add CI step that fails if cassettes change unexpectedly

**Success Criteria**:
- `just check-recordings` runs re-record and validates
- CI fails with clear message when recordings differ
- PR template reminds about recordings

### Milestone 5: Regression Tests for Known Bugs
**Goal**: Add recording tests that would have caught #40

- [ ] Create regression test for `reasoning_content` extraction (#40)
- [ ] Create regression test for CLI streaming
- [ ] Document pattern: "Every bug fix gets a recording test"
- [ ] Add to PR template: "Did you add/update cassette for bug fix?"

**Success Criteria**:
- Recording test exists that fails without #40 fix
- Documentation describes bug-to-recording-test pattern

## Justfile Commands

```makefile
# Run tests in playback mode (fast, default)
test:
    uv run pytest tests/ -v

# Re-record all cassettes with real APIs
test-record:
    #!/usr/bin/env bash
    echo "Recording fresh cassettes with real APIs..."
    VCR_RECORD_MODE=rewrite uv run pytest tests/ -v -k "integration or llm or agent"
    echo "Done. Review changes with: git diff tests/cassettes/"

# Check recordings - run before PR merge
test-check:
    #!/usr/bin/env bash
    echo "Checking for API behavior changes..."
    
    # Store baseline
    git stash push -m "test-check-stash" tests/cassettes/ 2>/dev/null || true
    
    # Re-record
    VCR_RECORD_MODE=rewrite uv run pytest tests/integration/ tests/test_llm.py tests/test_agent.py -v --tb=short
    
    # Check if anything changed
    if git diff --quiet tests/cassettes/ 2>/dev/null; then
        echo "✅ No API behavior changes detected"
        git stash pop 2>/dev/null || true
        exit 0
    else
        echo "⚠️  API behavior changed!"
        echo ""
        echo "Changed cassettes:"
        git diff --name-only tests/cassettes/
        echo ""
        echo "Review changes with: git diff tests/cassettes/"
        echo "If changes are expected: git add tests/cassettes/ && git commit"
        echo "If changes are unexpected: investigate API change"
        git checkout tests/cassettes/ 2>/dev/null || true
        git stash pop 2>/dev/null || true
        exit 1
    fi
```

## Configuration

### conftest.py

```python
import pytest

@pytest.fixture(scope="module")
def vcr_config():
    """VCR configuration for pytest-recording."""
    return {
        # Sanitize sensitive headers
        "filter_headers": ["authorization", "x-api-key"],
        
        # Sanitize query params
        "filter_query_parameters": ["api_key", "token", "key"],
        
        # Decode compressed responses for readability
        "decode_compressed_response": True,
        
        # Cassette storage
        "cassette_library_dir": "tests/cassettes",
        
        # Allow recording new interactions in existing cassettes
        "record_mode": "none",  # Default to playback only
    }

@pytest.fixture
def vcr_cassette_dir(request):
    """Organize cassettes by test file."""
    return f"tests/cassettes/{request.module.__name__}"
```

### Example Test

```python
# tests/test_llm_recording.py
import pytest
from src.llm import KimiProvider, ChatMessage
from src.config import load_config

@pytest.mark.vcr(record_mode="once")
@pytest.mark.asyncio
async def test_stream_chat_with_tools_extracts_reasoning():
    """
    Test that reasoning_content is extracted from streaming delta.
    
    This test would have caught #40. Recorded with Kimi thinking mode.
    """
    config = load_config()
    provider = KimiProvider(config)
    
    messages = [ChatMessage(role="user", content="Think then use a tool")]
    tools = [{"type": "function", "function": {"name": "test", "description": "test"}}]
    
    chunks = []
    async for chunk in provider.stream_chat_with_tools(messages, tools):
        chunks.append(chunk)
    
    response = "".join(chunks)
    
    # Behavior verification: reasoning extracted
    assert "[REASONING]" in response
    # Tool calls still work
    assert "[TOOL_CALLS]" in response
```

## CI/CD Integration

### GitHub Actions - PR Check

```yaml
# .github/workflows/test.yml
name: Tests

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v5
      
      - name: Run tests (playback mode)
        run: uv run pytest tests/ -v
```

### GitHub Actions - Recording Check (Optional)

```yaml
# .github/workflows/recording-check.yml
name: Recording Check

on:
  workflow_dispatch:  # Manual only - costs API calls

jobs:
  record:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup uv
        uses: astral-sh/setup-uv@v5
      
      - name: Check recordings
        env:
          KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: just test-check
```

## Success Criteria

- [ ] `pytest tests/` runs in <10 seconds (playback mode)
- [ ] `just test-check` re-records and validates API behavior
- [ ] API keys sanitized in all cassettes
- [ ] No async generator mocking in test suite
- [ ] Recording test exists for #40 regression
- [ ] Coverage ≥ 80%
- [ ] CI passes in playback mode
- [ ] Documentation explains recording workflow

## Dependencies

- `pytest-recording` - VCR integration for pytest
- `just` - Task runner (optional, can use make)

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| API costs from re-recording | Run check only on PRs, not every commit |
| Sensitive data in cassettes | Mandatory sanitization for API keys |
| Large cassette files | Organize by test file, .gitignore if needed |
| Flaky tests from API changes | Human review required for cassette changes |

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | PRD Created | Need trustworthy tests that verify real behavior |
| 2026-02-18 | pytest-recording chosen | Better pytest integration than vcrpy |
| 2026-02-18 | Option C workflow selected | Pre-PR recording check fits "guardrails" goal |
| 2026-02-18 | Sanitization required | API keys must not be in cassettes |
