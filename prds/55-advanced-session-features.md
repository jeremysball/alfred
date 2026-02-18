# PRD: Advanced Session Features - LLM Context Control

**Issue**: #55
**Status**: Ready for Implementation
**Priority**: Medium
**Created**: 2026-02-18
**Depends on**: PRD #54 (In-Memory Session Storage)

---

## Problem Statement

Once basic session storage exists (PRD #54), long conversations become unwieldy. The LLM cannot:
- Search its own conversation history for specific information
- Request specific slices of context ("remind me what we said about X")
- Control what appears in its own context window
- Navigate efficiently through hundreds of messages

---

## Solution Overview

Build advanced session navigation features on top of PRD #54. This is additive—PRD #54 provides the foundation, this PRD adds intelligence.

### Key Features

1. **Substring Search**: Search full conversation history for text matches
2. **LLM Context Control Tool**: Allow LLM to specify what goes into its context
3. **Smart Context Assembly**: ContextAssembler respects LLM preferences
4. **Summary on Demand**: Request summaries of specific message ranges

---

## Technical Architecture

### SessionManager Extensions (PRD #54 Base)

```python
class SessionManager:
    # ... PRD #54 methods ...
    
    def search_substring(self, query: str) -> list[tuple[int, Message]]:
        """Search all messages for substring matches.
        Returns (index, message) pairs.
        """
        
    def get_message_range(self, start: int, end: int) -> list[Message]:
        """Get messages by index range [start, end)."""
```

### ContextAssembler with LLM Control

```python
class ContextAssembler:
    """Builds LLM context with optional LLM-specified preferences."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.pending_preferences: ContextPreferences | None = None
    
    async def assemble_context(self) -> str:
        """Build context, respecting any pending LLM preferences."""
        prefs = self._consume_preferences()
        
        if prefs:
            messages = self._build_with_preferences(prefs)
        else:
            messages = self._build_default()
            
        return self._format_context(messages)
    
    def set_preferences(self, prefs: ContextPreferences) -> None:
        """Store preferences for next context assembly (via tool call)."""
        self.pending_preferences = prefs
        
    def _consume_preferences(self) -> ContextPreferences | None:
        """Get and clear pending preferences."""
        prefs = self.pending_preferences
        self.pending_preferences = None
        return prefs
```

### LLM Context Control Tool

```python
class SearchSessionHistory(Tool):
    """Tool allowing LLM to search its own conversation history."""
    
    name = "search_session_history"
    description = "Search the conversation history for specific text."
    
    async def execute(self, query: str) -> ToolResult:
        """Returns matching messages with their indices."""
        
class RequestContextSlice(Tool):
    """Tool allowing LLM to request specific conversation range."""
    
    name = "request_context_slice"
    description = """Request a specific slice of conversation for next context.
    
    Use when you need to focus on a specific part of the conversation
    rather than recent messages.
    """
    
    async def execute(
        self,
        start_message_index: int,
        end_message_index: int,
    ) -> ToolResult:
        """Sets preferences for next context assembly."""
        
class SummarizeMessageRange(Tool):
    """Tool to generate summary of specific message range."""
    
    name = "summarize_message_range"
    description = "Create a summary of messages from start_idx to end_idx."
    
    async def execute(
        self,
        start_idx: int,
        end_idx: int,
    ) -> ToolResult:
        """Generates and stores summary. SessionManager holds both raw messages AND summary."""
        
        # Generate summary via LLM
        summary = await self._generate_summary(start_idx, end_idx)
        
        # Store in SessionManager (raw messages already there, now add summary)
        self.session_manager.store_summary(start_idx, end_idx, summary)
        
        return ToolResult(content=summary)
```

### Data Models

```python
@dataclass
class ContextPreferences:
    """LLM-specified context assembly preferences."""
    message_range: tuple[int, int] | None = None  # (start, end) indices
    include_search_results: bool = False          # Include search matches
    max_context_messages: int | None = None       # Limit total messages
    
@dataclass
class SearchResult:
    """Result of session history search."""
    query: str
    matches: list[tuple[int, Message]]  # (index, message)
    total_matches: int
```

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Substring Search** | Add `search_substring()` to SessionManager | Can find text in conversation history |
| 2 | **Message Range Access** | Add `get_message_range()` to SessionManager | Can fetch arbitrary slices |
| 3 | **Search Tool** | `search_session_history` tool for LLM | LLM can search its history |
| 4 | **Context Slice Tool** | `request_context_slice` tool | LLM can request specific ranges |
| 5 | **Summary Tool** | `summarize_message_range` tool | LLM can get summaries on demand |
| 6 | **Smart Assembler** | ContextAssembler respects LLM preferences | Preferences affect next context |
| 7 | **Testing** | Full test coverage | >90% coverage, all tools work |

---

## Usage Examples

### LLM Searching History

```
User: What did we decide about the database?

LLM: [calls search_session_history("database")]
→ Returns matches at indices [5, 12, 34]

LLM: [calls request_context_slice(30, 40)]
→ Next context includes messages 30-39

LLM: We decided to use PostgreSQL with asyncpg (messages 34-36).
```

### LLM Requesting Summary

```
User: Summarize our discussion so far.

LLM: [calls summarize_message_range(0, current_idx)]
→ Returns summary text immediately

LLM: We've discussed the architecture (messages 1-20), 
     then moved to implementation details (messages 21-45).
```

---

## Relationship to PRD #54

This PRD extends PRD #54:

| Feature | PRD #54 (Base) | This PRD (Advanced) |
|---------|----------------|---------------------|
| Session storage | ✅ In-memory | Same |
| Basic context | ✅ Full history | Same |
| Substring search | ❌ | ✅ Add to SessionManager |
| LLM context control | ❌ | ✅ Tools for LLM |
| Smart assembly | ❌ | ✅ ContextPreferences |
| Summary on demand | ❌ | ✅ SummarizeMessageRange tool |

---

## Success Criteria

- [ ] LLM can search conversation history
- [ ] LLM can request specific message ranges
- [ ] LLM can get summaries of any range
- [ ] ContextAssembler respects LLM preferences
- [ ] All tools work in streaming mode
- [ ] Tests >90% coverage

---

## Dependencies

- PRD #54 (In-Memory Session Storage) must be complete
- Existing tool system
- LLM provider with tool support

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | Separate PRD from #54 | Keeps #54 minimal, this is additive complexity |
| 2026-02-18 | Summaries returned immediately | Assembler decides storage; SessionManager stays pure |
| 2026-02-18 | Preferences consumed once | Prevents stale preferences accumulating |
