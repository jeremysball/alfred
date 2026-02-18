# PRD: In-Memory Session Storage

**Issue**: #54  
**Status**: Ready for Implementation  
**Priority**: High  
**Created**: 2026-02-18

---

## Problem Statement

The CLI starts fresh with every message. Alfred has no conversation memory—each user input is processed in isolation. Users cannot refer to "what we just discussed," ask follow-up questions, or build context over multiple turns. This makes the CLI nearly unusable for any non-trivial task.

---

## Solution Overview

Implement in-memory session storage that maintains conversation history during the CLI session. This is intentionally minimal: no persistence, no summarization, just raw message history injected into context.

**Key Principle**: This PRD delivers immediate value (working CLI conversations) and serves as the foundation for PRD #53 (full session system with persistence, summarization, and semantic retrieval).

---

## Technical Architecture

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **In-memory only** | Zero complexity, immediate delivery |
| **No message limit** | Fill context window; PRD #53 will add compaction |
| **No persistence** | Survives only for process lifetime; PRD #53 adds JSONL |
| **Single session** | CLI has one active session; PRD #53 adds session management |

### Data Model

```python
@dataclass
class Session:
    """In-memory conversation session."""
    session_id: str          # UUID
    created_at: datetime
    messages: list[Message]  # Chronological exchange history

@dataclass
class Message:
    """Single exchange turn."""
    timestamp: datetime
    role: "user" | "assistant" | "system"
    content: str
```

### Context Injection

```
User Input
    ↓
SessionManager.get_messages() → Returns all messages
    ↓
Build context: System Prompt + Session History + User Input
    ↓
LLM Response
    ↓
Append assistant message to session
```

---

## Milestone Roadmap

| # | Milestone | Description | Success Criteria |
|---|-----------|-------------|------------------|
| 1 | **Session Data Model** | Create Session and Message dataclasses | Can instantiate and manipulate session objects |
| 2 | **Session Manager** | Singleton manager holding active session; append-only message log | Session persists across CLI interactions |
| 3 | **Context Integration** | Inject session messages into LLM context before system prompt | LLM sees full conversation history |
| 4 | **CLI Wiring** | Wire SessionManager to CLI chat loop; create/reset on startup | CLI maintains conversation context |
| 5 | **Testing** | Unit tests for session manager; integration test for CLI flow | >90% coverage on new code |

---

## Implementation Details

### SessionManager Interface

```python
class SessionManager:
    """Source of truth for session data. Handles storage, retrieval, and serialization.
    
    Never triggers compaction automatically. Creates/stores summaries only when
    explicitly requested by ContextAssembler. This ensures SessionManager remains
    a pure data layer that can fully serialize the conversation at any point.
    """
    
    _instance: SessionManager | None = None
    _session: Session | None = None
    
    @classmethod
    def get_instance(cls) -> SessionManager:
        """Get or create singleton instance."""
        
    def start_session(self) -> Session:
        """Create new session. Clears any existing session."""
        
    def add_message(self, role: str, content: str) -> None:
        """Append message to current session."""
        
    def get_messages(self, start_idx: int = 0, end_idx: int | None = None) -> list[Message]:
        """Get message slice by index range. Returns all if no range specified."""
        
    def get_substring_matches(self, query: str) -> list[tuple[int, Message]]:
        """Search messages for substring matches. Returns (index, message) pairs."""
        
    def create_summary(self, start_idx: int, end_idx: int) -> str:
        """Generate summary of message range via LLM. Stores and returns summary."""
        
    def get_summaries(self) -> list[Summary]:
        """Get all stored summaries for this session."""
        
    def get_full_session(self) -> Session:
        """Return complete session for serialization. Source of truth."""
        
    def clear_session(self) -> None:
        """Clear current session."""
```
```

### ContextAssembler Interface

```python
class ContextAssembler:
    """Builds LLM context from sessions, memories, and other sources.
    
    Makes all decisions about what goes into context. Uses SessionManager
    as source of truth but decides which slices to fetch and how to format.
    """
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.context_preferences: ContextPreferences | None = None
    
    async def assemble_context(self) -> str:
        """Build full context for LLM prompt."""
        
    def set_context_preferences(self, prefs: ContextPreferences) -> None:
        """Apply LLM-specified preferences for next context assembly."""
        
    def request_summary(self, start_idx: int, end_idx: int) -> str:
        """Request SessionManager create summary of message range."""
        
    def search_session_substring(self, query: str) -> list[tuple[int, Message]]:
        """Search session history for substring matches."""
        
    def clear_preferences(self) -> None:
        """Clear LLM preferences after use."""

@dataclass
class ContextPreferences:
    """LLM-specified preferences for context assembly (via tool call)."""
    memory_ids: list[str] | None = None      # Specific memories to include
    session_range: tuple[int, int] | None = None  # (start, end) message indices
    include_summaries: bool = True           # Include session summaries
    max_messages: int | None = None          # Limit to N most recent
```

### LLM Context Control Tool

```python
class SetContextPreferences(Tool):
    """Tool allowing LLM to influence what appears in its context."""
    
    name = "set_context_preferences"
    description = """Control what information appears in your context for the next turn.
    
    Use this to:
    - Request specific memories by ID
    - Specify which part of the conversation to focus on
    - Limit context window to recent messages
    - Include/exclude session summaries
    """
    
    async def execute(
        self,
        memory_ids: list[str] | None = None,
        session_start_idx: int | None = None,
        session_end_idx: int | None = None,
        max_recent_messages: int | None = None,
        include_summaries: bool = True,
    ) -> ToolResult:
        """Store preferences for next context assembly."""
```

---

## Relationship to PRD #53

This PRD is intentionally scoped to deliver immediate value. PRD #53 will extend this foundation:

| Feature | This PRD (#54) | PRD #53 (Future) |
|---------|----------------|------------------|
| **Storage** | In-memory only | JSONL persistence |
| **Message limit** | None (fill context) | Configurable + compaction |
| **Summarization** | None | Automatic after timeout |
| **Session retrieval** | None | Semantic search of past sessions |
| **CLI commands** | Auto-start session | `/sessions`, `/resume`, `/newsession` |
| **Multi-session** | No | Yes |

**Migration Path**: PRD #53 will:
1. Replace in-memory storage with JSONL
2. Add session summarization
3. Add semantic retrieval
4. Add CLI session management commands

The data model (Session, Message) remains unchanged.

---

## Success Criteria

- [ ] CLI maintains conversation context across multiple messages
- [ ] User can refer to previous parts of the conversation
- [ ] Session cleared on CLI restart (expected behavior for this PRD)
- [ ] No perceptible latency increase
- [ ] All tests passing

---

## Dependencies

- Existing context system
- CLI chat loop
- No new external dependencies

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-18 | In-memory only | Fastest path to working CLI; persistence in PRD #53 |
| 2026-02-18 | No message limit | Simplicity; PRD #53 adds compaction |
| 2026-02-18 | Singleton SessionManager | CLI has one active session; PRD #53 generalizes |
