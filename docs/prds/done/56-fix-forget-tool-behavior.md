# PRD: Fix Forget Tool - ID-Based Deletion with Call Tracking Confirmation

**Issue**: #56  
**Status**: Ready for Implementation  
**Priority**: High  
**Created**: 2026-02-18

---

## Problem Statement

The current `forget` tool has critical flaws:

1. **Over-deletion**: Deletes 4 memories when only 2 were appropriate - no precision control
2. **Broken confirmation**: The `confirm` parameter doesn't actually work - model can set it to true without user awareness
3. **Semantic-only targeting**: Relies entirely on similarity matching rather than explicit identification

**User Impact**: Users lose memories they wanted to keep because the tool is too aggressive and lacks proper safeguards.

---

## Solution Overview

Redesign the forget tool with two key principles:

### 1. ID-Based Deletion
- Semantic search finds candidate memories
- Model must specify exact memory ID(s) to delete
- No bulk deletion by similarity alone

### 2. Call-Tracking Confirmation
- First call: Returns candidates, asks for confirmation
- Tracks the pending deletion request
- Second call: Executes deletion if same ID(s) requested
- No `confirm` parameter - confirmation is implicit in the call sequence

---

## Current vs New Behavior

### Current (Broken)
```
User: Delete my memory about San Francisco

LLM: [calls forget with query="San Francisco", confirm=true]
→ Deletes 4 memories including "San Francisco", "California", "Bay Area", "Golden Gate"
```

### New (Fixed)
```
User: Delete my memory about San Francisco

LLM: [calls forget with query="San Francisco"]
→ Returns candidates with IDs:
   - f926ff7f: "User lives in San Francisco" (similarity: 0.95)
   - a1b2c3d4: "User visited San Francisco last year" (similarity: 0.82)
   
→ LLM: "I found these memories about San Francisco. Which would you like me to delete?"

User: Delete the first one

LLM: [calls forget with memory_id="f926ff7f"]
→ "Please confirm: Delete 'User lives in San Francisco' (f926ff7f)?"

User: Yes, delete it

LLM: [calls forget with memory_id="f926ff7f"]
→ Deleted successfully (second call executes)
```

---

## Technical Architecture

### Data Model

```python
@dataclass
class PendingDeletion:
    """Tracks a deletion request awaiting confirmation."""
    memory_id: str
    content_preview: str
    requested_at: datetime
    request_count: int  # How many times this ID has been requested
```

### ForgetTool Redesign

```python
class ForgetTool(Tool):
    """Delete memories by exact ID with call-tracking confirmation."""
    
    name = "forget"
    description = """Delete a memory by its exact ID. 
    
    First call: Returns candidates (if query provided) or confirms deletion target.
    Second call: Executes deletion of the specified memory ID.
    
    The tool tracks calls - you must request the same memory ID twice 
    (across two separate calls) for deletion to execute.
    """
    
    _pending_deletions: dict[str, PendingDeletion] = {}  # memory_id -> PendingDeletion
    
    async def execute(
        self,
        memory_id: str | None = None,
        query: str | None = None,
    ) -> ToolResult:
        """
        Args:
            memory_id: Exact memory ID to delete (required for deletion)
            query: Search query to find candidates (only for discovery phase)
        
        Returns:
            - If query provided: List of candidates with IDs
            - If memory_id provided (first call): Confirmation request
            - If memory_id provided (second call): Deletion result
        """
```

### Execution Flow

```
Case 1: Query provided (discovery phase)
  → Search memories by similarity
  → Return candidates with IDs
  → No deletion attempted

Case 2: memory_id provided, not in pending
  → Create PendingDeletion
  → Return confirmation request
  → "Please confirm deletion of [memory_id]: '[content preview]'"

Case 3: memory_id provided, already pending
  → Execute deletion
  → Remove from pending
  → Return success

Case 4: memory_id provided, pending expired (>5 min old)
  → Reset pending with new timestamp
  → Return confirmation request
```

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Remove confirm parameter** | Eliminate the `confirm` parameter from ForgetTool | Tool signature updated, old behavior removed |
| 2 | **Add PendingDeletion tracking** | Implement call-tracking mechanism | Pending deletions stored and retrieved correctly |
| 3 | **Implement two-call pattern** | First call returns confirmation, second executes | Test: two identical calls required for deletion |
| 4 | **Add query-only mode** | Support query parameter for candidate discovery | Returns ranked candidates with IDs |
| 5 | **Add expiration logic** | Pending deletions expire after 5 minutes | Test: old pending requests reset |
| 6 | **Update tool description** | Rewrite description to explain two-call pattern | LLM understands it must call twice |
| 7 | **Tests** | Full test coverage for new behavior | >90% coverage, all edge cases tested |
| 8 | **Integration test** | Verify end-to-end flow with actual LLM | Manual test confirms two-call requirement |

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| User requests different ID on second call | Treats as new first call for new ID, old pending expires |
| User waits >5 minutes between calls | First pending expires, new confirmation required |
| Memory already deleted between calls | Returns "Memory not found" error |
| Invalid memory_id | Returns "Memory not found" with suggestions |
| Multiple IDs in single request | Each ID tracked separately, all must be confirmed |
| Tool called rapidly in succession | Each call increments request_count, still needs 2+ calls |

---

## API Changes

### Current Signature (Broken)
```python
async def execute(
    self,
    query: str,
    confirm: bool = False,  # ← This doesn't work
) -> ToolResult
```

### New Signature (Fixed)
```python
async def execute(
    self,
    memory_id: str | None = None,
    query: str | None = None,
) -> ToolResult
```

### Tool Description (New)
```
Delete a memory by its exact ID. This tool requires two calls to execute:

1. First call: Provide memory_id to mark for deletion (confirmation requested)
2. Second call: Provide the same memory_id again to execute deletion

Alternatively, use query (without memory_id) to search for candidates.

Parameters:
- memory_id: The exact ID of the memory to delete. Must be called twice 
  with the same ID for deletion to occur.
- query: Search query to find memory candidates. Returns list with IDs.
  Use this to find the memory_id before deleting.

Examples:
- Find candidates: forget(query="San Francisco") → returns list
- Mark for deletion: forget(memory_id="abc123") → "Please confirm..."
- Execute deletion: forget(memory_id="abc123") → "Deleted successfully"
```

---

## Success Criteria

- [x] Deletion requires exactly 2 calls with same memory_id
- [x] Query mode returns candidates without deleting anything
- [x] Pending deletions expire after 5 minutes
- [x] Tool description clearly explains two-call pattern
- [x] All existing tests updated and passing
- [x] New tests cover: two-call pattern, expiration, edge cases
- [x] Manual test confirms LLM uses it correctly

---

## Dependencies

- Existing memory store
- Existing search functionality
- Tool registry system

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Remove confirm parameter | Model could set confirm=true without user knowledge |
| 2026-02-18 | Two-call confirmation pattern | Forces LLM to show user what will be deleted |
| 2026-02-18 | ID-based only (no bulk by similarity) | Prevents accidental mass deletion |
| 2026-02-18 | 5-minute expiration | Balance between UX safety and convenience |
