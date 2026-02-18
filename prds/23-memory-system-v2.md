# PRD: Memory System V2 - Complete CRUD with Semantic Search

## Overview

**Issue**: #38  
**Parent**: #10 (Alfred - The Rememberer)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-17

Build a complete memory system with Create, Read, Update, Delete operations and semantic search. This PRD consolidates lessons from M4 (Vector Search) and supersedes M8 (Capabilities) with a tool-based approach.

---

## Problem Statement

The current memory system has:
- ✅ **Read**: Semantic search and retrieval (implemented in M4)
- ✅ **Create**: `remember` tool for saving memories (just implemented)
- ❌ **Update**: No way to modify existing memories
- ❌ **Delete**: No way to remove memories
- ❌ **Search API**: No direct search tool for agent-initiated queries

Users need full CRUD operations to manage their memory store effectively.

---

## Lessons Learned

### 1. Tools Over Capabilities
**Decision**: Use tools, not a separate capability system.

**Rationale**:
- Tools run in main process with full context access
- No subprocess overhead or serialization issues
- Simpler architecture: one tool registry, one execution model
- Agent already has tool-calling infrastructure

**Implementation**: `remember` tool in `src/tools/remember.py` instead of M8's capability registry.

### 2. Async-First Design
**Lesson**: Tools must be async-compatible since the memory store uses async operations.

**Pattern**:
```python
# Synchronous execute() returns error message
# Asynchronous execute_stream() does the actual work
async def execute_stream(self, **kwargs) -> AsyncIterator[str]:
    await self._memory_store.add_entries([entry])
    yield result
```

### 3. Memory Store Injection
**Pattern**: Inject `MemoryStore` into tools at registration time:
```python
remember_tool = RememberTool()
remember_tool.set_memory_store(memory_store)
register_tool(remember_tool)
```

---

## Solution Overview

### Core Concept
Extend the existing memory system with three additional tools:
1. **`search_memories`** - Query memories with filters
2. **`update_memory`** - Modify existing memory content/importance/tags
3. **`forget`** - Remove memories by content match or ID

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent Loop                           │
├─────────────────────────────────────────────────────────────┤
│  User Message → LLM decides → Tool Call → Execute → Result  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   remember   │    │search_memories│   │   forget     │
│   (CREATE)   │    │   (READ)     │    │  (DELETE)    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                   ┌──────────────────┐
                   │   MemoryStore    │
                   │  (CRUD + Search) │
                   └──────────────────┘
                              │
                              ▼
                   ┌──────────────────┐
                   │ memories.jsonl   │
                   │  (Persistence)   │
                   └──────────────────┘
```

---

## File Structure

```
src/
├── tools/
│   ├── remember.py          # CREATE (already implemented)
│   ├── search_memories.py   # READ with filters
│   ├── update_memory.py     # UPDATE existing
│   └── forget.py            # DELETE by query/ID
├── memory.py                # MemoryStore CRUD operations
└── search.py                # Semantic search (already implemented)
```

---

## MemoryStore Extensions

### Current Methods (Existing)
```python
class MemoryStore:
    async def add_entries(self, entries: list[MemoryEntry]) -> None
    async def get_all_entries(self) -> list[MemoryEntry]
    async def search(self, query: str, top_k: int = 10, ...) -> list[MemoryEntry]
    async def clear(self) -> None
```

### New Methods Needed
```python
    async def update_entry(
        self,
        search_query: str,  # Find by semantic match
        new_content: str | None = None,
        new_importance: float | None = None,
    ) -> tuple[bool, str]  # (success, message)
    
    async def delete_entries(
        self,
        query: str,  # Delete by semantic match
    ) -> tuple[int, str]  # (count_deleted, message)
```

---

## Tool Specifications

### 1. search_memories Tool

```python
class SearchMemoriesTool(Tool):
    """Search through saved memories."""
    
    name = "search_memories"
    description = "Search through your memory store for relevant information"
    
    def execute(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        """Search memories and return formatted results."""
```

**Usage Examples**:
- `search_memories(query="Python preferences")`
- `search_memories(query="what did we discuss last week")`
- `search_memories(query="important facts")`

### 2. update_memory Tool

```python
class UpdateMemoryTool(Tool):
    """Update an existing memory's content or importance."""
    
    name = "update_memory"
    description = "Update an existing memory with new information"
    
    def execute(
        self,
        search_query: str,  # Find memory to update
        new_content: str = "",
        new_importance: float = -1,  # -1 means don't change
    ) -> str:
        """Find memory matching query and update it."""
```

**Usage Examples**:
- `update_memory(search_query="user name", new_content="User name is Jasmine (goes by Jaz)")`
- `update_memory(search_query="Python", new_importance=0.9)`
- `update_memory(search_query="work location", new_content="User works remotely from Portland", new_importance=0.8)`

**Note**: Updates only the top matching memory. If multiple memories need updating, call multiple times with more specific queries.

### 3. forget Tool

```python
class ForgetTool(Tool):
    """Remove memories from the store."""
    
    name = "forget"
    description = "Delete memories matching a semantic query"
    
    def execute(
        self,
        query: str,  # Delete semantically similar memories
    ) -> str:
        """Delete memories matching query."""
```

**Usage Examples**:
- `forget(query="old project idea")`
- `forget(query="incorrect information about my age")`
- `forget(query="temporary todos from last week")`

**Note**: No confirmation mechanism - the LLM's interpretation of user intent is the safety check.

---

## Implementation Plan

### Phase 1: MemoryStore Extensions
- [x] Add `update_entry()` method to MemoryStore
- [x] Add `delete_entries()` method to MemoryStore
- [x] Add entry_id generation (hash of timestamp + content)
- [x] Tests for all new methods

### Phase 2: Search Tool
- [x] Create `SearchMemoriesTool`
- [x] Register with tool registry
- [x] Tests for search functionality
- [~] Update SOUL.md with search instructions (moved to AGENTS.md)

### Phase 3: Update Tool
- [x] Create `UpdateMemoryTool`
- [x] Handle partial updates (content and/or importance)
- [x] Tests for update operations
- [~] Update SOUL.md with update instructions (moved to AGENTS.md)

### Phase 4: Forget Tool
- [ ] Create `ForgetTool`
- [ ] Tests for deletion
- [ ] Update SOUL.md with deletion instructions

### Phase 5: Integration
- [x] Update AGENTS.md with memory management guidelines
- [ ] Add memory management examples to documentation
- [ ] Integration tests for full CRUD workflow

---

## Agent Instructions (SOUL.md Updates)

```markdown
## Memory Management

You have four memory tools available:

### remember (CREATE)
Use when you learn something worth keeping:
- User explicitly says "remember..."
- Important preferences or facts
- Project context that spans conversations

### search_memories (READ)
Use when you need to find past information:
- User asks "what did I say about..."
- You need context from previous conversations
- Searching for specific facts you recall storing

### update_memory (UPDATE)
Use when information changes:
- User corrects something you remembered
- Details need refinement
- Importance changes over time

### forget (DELETE)
Use when information is obsolete or wrong:
- User says "forget that" or "that's wrong"
- Old temporary information (todos, etc.)
- Use semantic queries to find what to delete

### Best Practices
- **Create liberally**: Better to remember too much than too little
- **Search before asking**: Check if you already know the answer
- **Update promptly**: Keep information current
- **Delete matches**: Semantic search finds what to delete
```

---

## Acceptance Criteria

- [x] `search_memories` tool returns relevant memories
- [x] `update_memory` tool modifies existing memories correctly
- [ ] `forget` tool deletes by semantic query
- [ ] All CRUD operations have comprehensive tests
- [ ] Agent knows when to use each tool
- [ ] Documentation updated for all tools

---

## Success Criteria

- Agent can perform full CRUD on memories
- Semantic search returns >80% relevant results
- Updates preserve embedding (or regenerate if content changes)
- Deletion uses semantic matching to find targets
- All operations are idempotent where appropriate

---

## Dependencies

- Existing `MemoryStore` and embedding system
- `remember` tool (already implemented)
- Tool registry infrastructure

---

## Future Enhancements (Out of Scope)

- Memory compaction/consolidation (M9)
- Automatic memory distillation (M10)
- Batch memory operations
- Memory export/import
- Vector index optimization (FAISS/Annoy)
- Structured tags/categories (if needed for bulk operations)

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Tools over capabilities | Simpler, main process, no overhead | All memory operations are tools |
| 2026-02-17 | Async execute_stream | MemoryStore is async | Tools use async iteration |
| 2026-02-17 | No confirmation for delete | LLM interprets intent; confirming twice is theater | Delete by semantic query only |
| 2026-02-17 | No tags | Embeddings handle categorization better | Simpler MemoryEntry, rely on semantic search |
| 2026-02-17 | Entry IDs from hash | Stable identifiers without tracking max ID | Memories have unique IDs (SHA256 of timestamp:content) for future use |
