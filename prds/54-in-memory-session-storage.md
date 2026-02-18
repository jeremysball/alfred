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
    """Singleton manager for the active CLI session."""
    
    _instance: SessionManager | None = None
    _session: Session | None = None
    
    @classmethod
    def get_instance(cls) -> SessionManager:
        """Get or create singleton instance."""
        
    def start_session(self) -> Session:
        """Create new session. Clears any existing session."""
        
    def add_message(self, role: str, content: str) -> None:
        """Append message to current session."""
        
    def get_messages(self) -> list[Message]:
        """Get all messages in chronological order."""
        
    def clear_session(self) -> None:
        """Clear current session."""
```

### Context Assembly

```python
async def assemble_context(self) -> str:
    """Build context with session history."""
    base_prompt = self._load_system_prompt()
    session_messages = self.session_manager.get_messages()
    
    history_parts = []
    for msg in session_messages:
        prefix = "User" if msg.role == "user" else "Assistant"
        history_parts.append(f"{prefix}: {msg.content}")
    
    return f"""{base_prompt}

## CONVERSATION HISTORY

{chr(10).join(history_parts)}

## CURRENT MESSAGE
"""
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
