# PRD: M8 - Capabilities System (ARCHIVED)

## Status: **SUPERSEDED**

**Decision Date**: 2026-02-17  
**Decision**: Use **tools** instead of capabilities for memory operations  
**Reason**: Tools run in main process, simpler architecture, no skill overhead

---

## Historical Context

This PRD originally proposed a separate "capabilities" system for automatic model-driven actions. We have **archived this approach** in favor of extending the existing **tool system**.

## Why Tools Won

| Capability Approach | Tool Approach |
|---------------------|---------------|
| Separate registry to maintain | Reuse existing `ToolRegistry` |
| Subprocess or isolated execution | Runs in main process with full context |
| Complex confidence scoring | Model decides via tool descriptions |
| Another abstraction to learn | Natural extension of existing pattern |
| Context serialization issues | Direct memory access |

## What We Built Instead

### Remember Tool (`src/tools/remember.py`)

```python
class RememberTool(Tool):
    """Save a memory to the unified memory store.
    
    Use this when the user asks you to remember something,
    or when you learn important facts, preferences, or context
    that would be useful to recall in future conversations.
    """
    
    name = "remember"
    description = "Save a memory to the unified memory store for future retrieval"
```

**Usage:**
- Agent calls `remember(content, importance, tags)` via normal tool use
- Memory store injected at tool initialization
- No separate routing or confidence scoring needed

### Integration

```python
# In src/alfred.py
register_builtin_tools(memory_store=self.memory_store)
```

The tool is registered with the memory store injected, so it has direct access to save entries.

### Agent Instructions (in SOUL.md)

The SOUL.md tells Alfred:
- He has a `remember` tool available
- When to use it (user says "remember...", important facts, preferences)
- That memories are auto-retrieved via semantic search
- How to set importance and tags

## What Still Works from This PRD

The **search and retrieval** aspects are already implemented:

- `MemorySearcher` in `src/search.py` - semantic search with hybrid scoring
- `ContextBuilder` - injects relevant memories into prompts
- Automatic retrieval before each response

## What We Replaced

| Original Plan | Replacement |
|---------------|-------------|
| `Capability.can_handle()` confidence scoring | Model decides via tool descriptions in system prompt |
| `Capability.execute()` | Tool `execute()` method |
| `CapabilityRegistry.route()` | Agent's existing tool-calling logic |
| Separate `CAPABILITIES/` directory | `src/tools/remember.py` + future tools as needed |

## Future Work

If we need more "automatic" behaviors:

1. **Extend tool descriptions**: Better prompts in SOUL.md about when to use tools
2. **Add more memory tools**: `forget`, `update_memory`, `search_memories` if needed
3. **Background distillation**: Periodic process to extract memories from conversation history (can use same `MemoryStore.add_entries()` API)

## Lessons Learned

1. **Prefer extending existing systems** over new abstractions
2. **Tools are capabilities** - they just needed better descriptions
3. **Main process execution** eliminates serialization headaches
4. **Model-driven means good prompting**, not complex routing logic

## References

- `src/tools/remember.py` - Implementation
- `skills/memory-system/SKILL.md` - Updated memory system docs
- `data/SOUL.md` - Agent instructions for memory usage
