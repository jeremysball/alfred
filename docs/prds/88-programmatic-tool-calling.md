# PRD #88: Programmatic Tool Calling

**Status**: Exploratory
**Priority**: Low (Long-term)
**Created**: 2026-02-22
**GitHub Issue**: [#88](https://github.com/jeremysball/alfred/issues/88)

---

## Problem Statement

Traditional JSON-based tool calling creates inefficiencies:

1. **Wasted Token Space**: API responses dump raw metadata into the LLM context window
2. **High Costs**: Repeated tool call generation burns tokens
3. **Slow Multi-step Workflows**: Constant round-trips between LLM and server for each action

Example: Listing 50 files requires 50 individual tool calls, each returning full metadata, each requiring a separate LLM turn to process.

---

## Solution Overview

Allow the LLM to write executable Python code that orchestrates multiple tool calls in a single sandbox execution. The code runs locally, filters results, and returns only relevant data to the context window.

**Key benefits:**
- 30-50% reduction in token consumption
- Faster execution (fewer round-trips)
- Native programming logic (loops, conditionals, error handling)
- Context window optimization (only filtered results returned)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sandbox | `exec()` with namespace | Uses current system, minimal complexity |
| Tool access | All tools exposed | Trust the LLM, maintain consistency |
| Return handling | Auto-serialize return values | Simpler LLM experience |
| Compatibility | JSON tool calling remains as fallback | Safe migration path |
| Visibility | Show code blocks in output | Debugging and transparency |

---

## Technical Design

### Sandbox Architecture

```python
# Conceptual implementation
class CodeExecutionTool(Tool):
    name = "execute_code"

    async def execute(self, code: str) -> dict:
        # Build namespace with all tools
        namespace = {
            "read": self.tools.read,
            "write": self.tools.write,
            "edit": self.tools.edit,
            "bash": self.tools.bash,
            "remember": self.tools.remember,
            "search_memories": self.tools.search_memories,
            # ... all other tools
        }

        # Execute code in sandbox
        try:
            exec(code, {"__builtins__": safe_builtins}, namespace)
            result = namespace.get("_result", "Code executed successfully")
        except Exception as e:
            result = f"Error: {e}"

        # Auto-serialize and return
        return {"output": serialize(result)}
```

### LLM Usage Example

Instead of:
```
# Turn 1: LLM calls read("file1.txt")
# Turn 2: LLM calls read("file2.txt")
# Turn 3: LLM calls read("file3.txt")
# Turn 4: LLM synthesizes results
```

The LLM writes:
```python
files = ["file1.txt", "file2.txt", "file3.txt"]
contents = [read(f) for f in files]
_result = {"total_lines": sum(len(c.split("\n")) for c in contents)}
```

Single execution, filtered result returned to context.

---

## User Stories

1. **As Alfred**, I can write Python code to batch-process files so I complete tasks faster with fewer round-trips.

2. **As Alfred**, I can filter API responses programmatically so only relevant data enters my context window.

3. **As a user**, I can see the code Alfred executed so I understand what happened.

4. **As a user**, Alfred falls back to JSON tool calling if code execution fails so I'm never stuck.

---

## Success Criteria

- [ ] Code execution tool implemented with `exec()` sandbox
- [ ] All existing tools exposed in namespace
- [ ] Auto-serialization of return values working
- [ ] Code blocks visible in CLI/Telegram output
- [ ] JSON tool calling still works as fallback
- [ ] Token consumption reduced by 30%+ on multi-step tasks
- [ ] No security regressions (no file system escape, no network access beyond tools)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Code execution escape | Low | High | Restricted builtins, no `import`, no `eval` |
| Infinite loops | Medium | Medium | Execution timeout (5 seconds) |
| Serialization failures | Medium | Low | Fallback to string representation |
| LLM writes bad code | Medium | Low | Clear error messages, retry with JSON fallback |

---

## Implementation Milestones

### Phase 1: Core Implementation
- [ ] Create `CodeExecutionTool` class with `exec()` sandbox
- [ ] Build namespace with all tool references
- [ ] Implement safe builtins restriction
- [ ] Add execution timeout (5 seconds)
- [ ] Auto-serialize return values to JSON-safe format

### Phase 2: Integration
- [ ] Register tool in Alfred's tool registry
- [ ] Update TOOLS.md with code execution documentation
- [ ] Add code block rendering to CLI output
- [ ] Add code block rendering to Telegram output

### Phase 3: Testing & Polish
- [ ] Unit tests for sandbox security boundaries
- [ ] Integration tests for multi-tool workflows
- [ ] Token consumption benchmarks vs JSON tool calling
- [ ] Error handling and fallback to JSON mode

---

## Open Questions

1. **Memory access**: Should `remember()` and `search_memories()` work in code sandbox, or require explicit JSON calls?
2. **Import restrictions**: Should we allow whitelisted imports (e.g., `json`, `re`)?
3. **State persistence**: Should variables persist between code executions within a session?

---

## References

- Anthropic's Programmatic Tool Calling announcement
- Current Alfred tool system: `src/tools/`
- Context assembly: `src/context.py`
