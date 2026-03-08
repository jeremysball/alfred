# PRD: Tool Call Persistence and Context Visibility

**GitHub Issue**: #101  
**Priority**: High  
**Status**: ✅ COMPLETE (Merged via PR #103)

---

## 1. Problem Statement

### 1.1 Invisible Tool Execution
Currently, when Alfred uses tools to answer a question, the tool calls are not persisted in session history. Users see:

```
User: What files are in /tmp?
Assistant: I found 3 files in /tmp: a.txt, b.txt, c.txt
```

But they **don't see** that the assistant used the `bash` tool with `ls /tmp` to get that answer. This makes it impossible to:
- Debug what tools were used
- Understand how answers were derived
- Learn from past tool usage patterns

### 1.2 Lost Context
Tool calls and their outputs contain valuable context that could help the LLM in subsequent turns. Currently this context is lost after each turn.

### 1.3 No Context Inspection
Users have no way to see what Alfred currently "knows" - the system prompt, memories, and recent conversation context are invisible.

---

## 2. Solution Overview

### 2.1 Persist Tool Calls
Add `tool_calls` field to the Message dataclass and persist tool execution in session storage.

### 2.2 Include Tool Calls in Context
When building context for the LLM, include recent tool calls (configurable: last X calls or up to Y tokens).

### 2.3 Context Visibility Command
Add `/context` command that outputs the current system context as a system message in the chat.

### 2.4 Enhanced Tool Display
Show tool parameters as the first line inside the tool box for immediate visibility.

---

## 3. Detailed Requirements

### 3.1 Message DTO Extension

**Current Message dataclass:**
```python
@dataclass
class Message:
    idx: int
    role: Role
    content: str
    timestamp: datetime
    embedding: list[float] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
```

**New Message dataclass:**
```python
@dataclass
class ToolCallRecord:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    output: str
    status: Literal["success", "error"]
    insert_position: int = 0  # Character position in message.content where tool occurred
    sequence: int = 0          # Ordering when multiple tools at same position

@dataclass
class Message:
    idx: int
    role: Role
    content: str
    timestamp: datetime
    embedding: list[float] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    tool_calls: list[ToolCallRecord] | None = None  # NEW
```

**Design Decision:** Tool calls are attached to the assistant message that generated them. The `insert_position` field tracks where in the message text the tool execution occurred, enabling accurate reconstruction of the conversation flow during display.

### 3.2 Session Storage Format

Tool calls stored in `current.jsonl`:
```json
{
  "idx": 5,
  "role": "assistant",
  "content": "I found 3 files in /tmp...",
  "timestamp": "2026-03-02T20:00:00Z",
  "tool_calls": [
    {
      "tool_call_id": "call_abc123",
      "tool_name": "bash",
      "arguments": {"command": "ls /tmp"},
      "output": "a.txt\nb.txt\nc.txt",
      "status": "success",
      "insert_position": 11,
      "sequence": 0
    }
  ]
}
```

**Storage Decision:** Tool calls include `insert_position` (character offset in message text) and `sequence` (ordering for multiple tools at same position) to enable precise reconstruction of where tool execution occurred within the conversation flow.

### 3.3 Context Assembly with Tool Calls

**Config options:**
```toml
[context.tool_calls]
max_calls = 5          # Include last N tool calls
max_tokens = 2000      # Or up to N tokens (whichever is smaller)
include_output = true  # Include tool output or just call info
```

**Context format:**
```
## RECENT TOOL CALLS

1. bash: ls /tmp
   Output: a.txt, b.txt, c.txt

2. search_memories: "project setup"
   Output: Found 3 memories...
```

### 3.4 Tool Box Enhancement

**Current display:**
```
┌─ bash ─────────────────┐
│                        │
│ a.txt                  │
│ b.txt                  │
│ c.txt                  │
└────────────────────────┘
```

**Enhanced display:**
```
┌─ bash ─────────────────┐
│ ls /tmp                │
│                        │
│ a.txt                  │
│ b.txt                  │
│ c.txt                  │
└────────────────────────┘
```

### 3.5 /context Command

**Usage:** `/context`

**Output:** System message showing:
- System prompt (AGENTS.md + SOUL.md + USER.md + TOOLS.md)
- Relevant memories (summarized)
- Recent conversation history
- Recent tool calls
- Token counts for each section

---

## 4. Implementation Milestones

### Milestone 1: Tool Call Persistence

- [x] Add `ToolCallRecord` dataclass
- [x] Add `tool_calls` field to Message dataclass
- [x] Update session storage serialization/deserialization
- [x] Update Alfred to capture and store tool calls
- [x] Test: Tool calls persisted in current.jsonl

### Milestone 2: Context Assembly with Tool Calls

- [x] Add `[context.tool_calls]` config section
- [x] Update ContextBuilder to include tool calls
- [x] Implement token budget for tool calls in context
- [x] Test: Tool calls included in LLM context

### Milestone 3: Tool Box Enhancement

- [x] Modify message_panel.py to show arguments first
- [x] Format arguments as JSON or key=value pairs
- [x] Test: Arguments visible in tool box

### Milestone 4: /context Command

- [x] Add `/context` command handler
- [x] Format system context for display
- [x] Show token counts per section
- [x] Test: Context displays correctly

### Milestone 5: Integration and Cleanup

- [x] All tests pass
- [ ] Documentation updated
- [ ] PR merged

---

## 5. Command Architecture Refactoring

**Date:** 2026-03-03

After implementing individual command handlers in `AlfredTUI`, the command logic was refactored into a structured command architecture:

### Command Base Class

```python
class Command(ABC):
    """Base class for TUI commands."""

    name: str           # Command name without leading slash
    description: str    # Brief description for completion menu

    @abstractmethod
    def execute(self, tui: "AlfredTUI", arg: str | None) -> bool:
        """Execute the command."""
        ...
```

### Benefits

- **Single Responsibility:** Each command is isolated in its own file
- **Testability:** Commands can be unit tested independently
- **Discoverability:** Commands auto-register via `__init__.py` registry
- **Completion Integration:** Description field populates completion menu automatically

### Commands Implemented

| Command | File | Description |
|---------|------|-------------|
| `/new` | `new_session.py` | Start a new conversation session |
| `/resume` | `resume_session.py` | Resume a previous session by ID |
| `/sessions` | `list_sessions.py` | List all available sessions |
| `/session` | `show_session.py` | Show current session info |
| `/context` | `show_context.py` | Display system context |

---

## 6. File Changes

### Modified Files
| File | Changes |
|------|---------|
| `src/session.py` | Add ToolCallRecord, update Message |
| `src/session_storage.py` | Serialize/deserialize tool_calls |
| `src/alfred.py` | Capture tool calls from agent |
| `src/context.py` | Include tool calls in context |
| `src/config.py` | Add tool_calls config section |
| `src/interfaces/cli.py` | Add /context command |
| `src/interfaces/pypitui/message_panel.py` | Show arguments first |
| `src/interfaces/pypitui/tui.py` | Use command architecture |
| `templates/config.toml` | Add tool_calls config defaults |

### New Files
| File | Purpose |
|------|---------|
| `src/interfaces/pypitui/commands/base.py` | Abstract base class for TUI commands |
| `src/interfaces/pypitui/commands/__init__.py` | Command registry and discovery |
| `src/interfaces/pypitui/commands/new_session.py` | `/new` command implementation |
| `src/interfaces/pypitui/commands/resume_session.py` | `/resume` command implementation |
| `src/interfaces/pypitui/commands/list_sessions.py` | `/sessions` command implementation |
| `src/interfaces/pypitui/commands/show_session.py` | `/session` command implementation |
| `src/interfaces/pypitui/commands/show_context.py` | `/context` command implementation |

---

## 8. Testing Strategy

- Unit tests for serialization/deserialization
- Integration tests for context assembly
- Manual testing for /context command
- Manual testing for tool box display

---

## 9. Success Criteria

- [x] Tool calls visible in session history
- [x] Tool calls included in LLM context
- [x] /context command works
- [x] Tool arguments visible in UI
- [x] All tests pass

---

## 10. Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| Session file size increase | Configurable limits on stored tool calls |
| Context token budget exceeded | Respect max_tokens config, truncate if needed |
| Backward compatibility | Handle missing tool_calls field gracefully |

---

## 11. Design Decisions Log

### Decision: Tool Call Placement Within Messages
**Date:** 2026-03-02  
**Decision:** Store `insert_position` and `sequence` in `ToolCallRecord` to track exactly where within a message's text the tool execution occurred.

**Rationale:**
- Enables accurate reconstruction of conversation flow when displaying messages
- Supports multiple tool calls at the same position (ordered by sequence)
- Maintains relationship between text and tool execution for context assembly

**Impact:**
- `ToolCallRecord` includes two additional integer fields
- Storage format includes these fields in JSON
- Loading code must handle backward compatibility (missing fields default to 0)

### Decision: Attach Tool Calls to Assistant Messages
**Date:** 2026-03-02  
**Decision:** Tool calls are stored on the assistant message that generated them, not as separate messages.

**Rationale:**
- Natural mapping: the assistant message at idx=X with `tool_calls` triggered those tools
- Tool results follow as separate messages (idx=X+1, X+2, etc.)
- Enables easy lookup of which assistant response triggered which tools

**Example:**
```
idx=0: User message
idx=1: Assistant message with tool_calls=[...]  ← Tools triggered here
idx=2: Tool result (bash output)
idx=3: Assistant final response
```

### Decision: Capture via Existing Callback
**Date:** 2026-03-02  
**Decision:** Use the existing `tool_callback` mechanism in `Alfred.chat_stream()` to capture tool calls, avoiding changes to the Agent class.

**Rationale:**
- Agent already emits `ToolStart`, `ToolOutput`, `ToolEnd` events
- Can accumulate tool call data and attach to assistant message when saved
- Minimizes changes to core agent loop
- Existing event data provides all needed information (id, name, args, output, status)

**Implementation:**
1. Track `full_response` length when `ToolStart` fires → that's `insert_position`
2. Accumulate tool output from `ToolOutput` chunks
3. On `ToolEnd`, create `ToolCallRecord` with complete data
4. When assistant message saved, include accumulated `tool_calls` list
