# PRD: Interleaved Tool Calls and Thinking Blocks

## Issue Reference

**GitHub Issue**: [#155](https://github.com/jeremysball/alfred/issues/155)  
**Priority**: Medium  
**Status**: Draft

---

## Problem Statement

Currently, Alfred's TUI (PyPiTUI) appends tool calls and thinking blocks to the end of messages rather than displaying them at the exact point in the conversation stream where they were triggered. This creates several UX problems:

1. **Temporal Disconnect**: Users see the LLM's response before seeing the tool calls or reasoning that produced it, even though they happened in the opposite order.

2. **Loss of Context**: When the LLM reasons about something, then calls a tool, then reasons some more, these phases appear as separate disconnected messages rather than a continuous flow.

3. **Cognitive Overhead**: Users must mentally reconstruct the actual sequence of events from the disjointed display.

### Current Behavior

```
[User] What files were modified recently?

[Assistant] I'll check the recent git history for you.
        [message ends, streaming pauses]
        [separate tool box appears]
        [thinking appears at end]
        [final response appears]
```

### Desired Behavior

```
[User] What files were modified recently?

[Assistant] I'll check the recent git history for you.
        ┌─ thinking ─────────┐
        │ User wants recent  │
        │ modified files.    │
        │ I'll use bash with │
        │ git status.        │
        └────────────────────┘
        ┌─ bash (running) ───┐
        │ git status         │
        └────────────────────┘
        [output streams in real-time]
        ┌─ thinking ─────────┐
        │ Based on git       │
        │ output, I can see  │
        │ 3 modified files.  │
        └────────────────────┘
        Here are the files modified recently:
        - src/main.py
        - tests/test_main.py
        - README.md
```

---

## Solution Overview

Implement a **streaming message buffer** that captures and interleaves all event types (text, tool calls, thinking blocks) in their actual chronological order. This requires changes to:

1. **Message rendering pipeline**: Support mixed content blocks that can be appended incrementally
2. **Agent loop integration**: Stream events as they happen, not batched at the end
3. **Content block types**: Add thinking block as a first-class content type
4. **TUI layout**: Handle dynamic content insertion mid-message

---

## Success Criteria

- [x] Tool calls appear inline at the exact point in the conversation where triggered (Web UI ✅)
- [x] Thinking blocks (if enabled) appear inline during streaming (Web UI ✅)
- [x] Content renders chronologically as events occur, not batched at message end (Web UI ✅)
- [x] Existing functionality (tool expansion, copy/paste, scrollback) continues to work (Web UI ✅)
- [x] Web UI uses button-style tool calls without borders (Web UI ✅)
- [ ] TUI interleaving (if desired - currently unchanged with bordered boxes)

---

## Milestones

### Milestone 1: Content Block Architecture Refactoring ✅

**Goal**: Extend the content block system to support chronological event ordering.

**Changes**:
- ~~Refactor `ContentBlock` in `message_panel.py` to include a `timestamp` or `sequence` field~~ (TUI unchanged)
- Add content block sequencing to `chat-message.js` with `_contentBlocks` array and `_sequenceCounter`
- Support block types: `text`, `reasoning`, `tool` with chronological ordering
- Render blocks in sequence order via `_renderContentBlocks()`

**Validation**:
- ✅ Content blocks maintain proper ordering when multiple types are interleaved
- ✅ Existing tool call display continues to work

---

### Milestone 2: Streaming Event Buffer

**Goal**: Create an event buffer that captures all stream events in chronological order.

**Changes**:
- Create `StreamingBuffer` class in `message_panel.py` or new module
- Buffer receives events: `text_chunk`, `thinking_start`, `thinking_chunk`, `thinking_end`, `tool_call_start`, `tool_call_chunk`, `tool_call_end`
- Buffer emits ordered `ContentBlock` updates to MessagePanel

**Validation**:
- Events emitted in order received
- Buffer handles rapid successive events without reordering

---

### Milestone 3: Agent Loop Integration

**Goal**: Modify the agent loop to emit streaming events instead of batched results.

**Changes**:
- Update `alfred/agent.py` to yield events as they occur during streaming
- Emit `thinking` events when reasoning content is received from LLM
- Emit tool call events at their actual trigger points
- Update TUI event handlers to process streaming events

**Validation**:
- Tool calls appear mid-stream, not at message end
- Thinking blocks render during LLM response streaming

---

### Milestone 4: Thinking Block Interleaving ✅

**Goal**: Interleave existing thinking block rendering within message streams.

**Changes**:
- Leverage existing collapsible thinking block UI
- Modify `appendReasoning()` to create/update reasoning blocks with sequence numbers
- Render thinking blocks inline via `_createReasoningBlockElement()`
- Theme-aware styling (respect kidcore, spacejam, default themes)

**Validation**:
- ✅ Thinking blocks appear inline at trigger point
- ✅ Collapsible/expansion continues to work
- ✅ Existing styling preserved

---

### Milestone 5: Message Reconstruction for Persistence

**Goal**: Ensure interleaved messages can be saved and restored correctly.

**Changes**:
- Update session storage format to preserve block ordering
- Modify `SessionStore` to save/restore mixed content blocks
- Handle backward compatibility with existing session files

**Validation**:
- Sessions with interleaved content save and reload correctly
- Old session format still loads (backward compatibility)

---

### Milestone 6: Web UI Interleaving ✅

**Goal**: Web UI displays interleaved content with parity to TUI.

**Changes**:
- ✅ Update Web UI message components to support mixed content blocks
- ✅ Implement thinking block rendering in web interface via `_contentBlocks` system
- ✅ Ensure WebSocket events stream in correct order (already supported)
- ✅ **Web UI only**: Remove tool call borders/backgrounds (button-only style)

**Validation**:
- ✅ Web UI shows interleaved behavior (reasoning, tools, text in chronological order)
- ✅ TUI keeps bordered boxes (unchanged)
- ✅ Web UI uses simplified button-style tool calls

---

## Technical Design

### Content Block Sequence System

```python
@dataclass
class SequencedContentBlock:
    """A content block with sequence information for chronological ordering."""
    type: Literal["text", "thinking", "tool_start", "tool_stream", "tool_end"]
    sequence: int  # Monotonic counter for ordering
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Event Types

```python
class StreamEventType(Enum):
    TEXT_CHUNK = "text_chunk"           # Regular text from LLM
    THINKING_START = "thinking_start"   # Reasoning block begins
    THINKING_CHUNK = "thinking_chunk"   # Reasoning content
    THINKING_END = "thinking_end"       # Reasoning block ends
    TOOL_START = "tool_start"           # Tool call initiated
    TOOL_CHUNK = "tool_chunk"           # Tool output streaming
    TOOL_END = "tool_end"               # Tool call completed
```

### Streaming Buffer

```python
class StreamingBuffer:
    """Buffers streaming events and produces ordered content blocks."""
    
    def __init__(self, message_panel: MessagePanel) -> None:
        self._panel = message_panel
        self._sequence = 0
        self._current_blocks: dict[str, SequencedContentBlock] = {}
    
    def emit(self, event_type: StreamEventType, content: str, metadata: dict | None = None) -> None:
        """Emit a streaming event."""
        self._sequence += 1
        # Create or update content block, notify panel
    
    def finalize(self) -> None:
        """Finalize all blocks and flush to panel."""
```

### Integration Points

1. **Agent Loop**: Yield `StreamEvent` objects instead of accumulating text
2. **TUI Handler**: Process events and call `StreamingBuffer.emit()`
3. **MessagePanel**: Render blocks by sequence, not by position
4. **Session Store**: Save blocks with sequence numbers

---

## UI/UX Specifications

### Thinking Block Design

- **Collapsed state**: Single line with indicator: "🧠 Thinking..." or similar
- **Expanded state**: Collapsible panel with subtle styling
- **Default**: Collapsed to avoid distraction
- **Toggle**: Click or Ctrl+T to expand/collapse
- **Styling**: Dim colors, italic text, distinct from main content

### Tool Call Interleaving

- Tool calls appear exactly where triggered in the stream
- Running state shows spinner/progress indicator
- Completion transitions to success/error state inline
- Output streams in real-time within the tool box
- **Visual simplification**: Remove border/background box, show only the tool button

### Visual Hierarchy

```
┌─ Assistant ──────────────────┐
│                              │
│ Here's what I found:         │
│                              │
│ ┌─ thinking (collapsed) ───┐ │
│ │ 🧠 Thinking...           │ │
│ └──────────────────────────┘ │
│                              │
│ ▶ bash ■■■ (running)         │
│   ls -la                     │
│   total 128                  │
│   drwxr-xr-x  5 user...      │
│                              │
│ Based on the directory...    │
│                              │
└──────────────────────────────┘
```

**Tool calls show as button-style elements without border boxes:**
- ▶ bash ■■■ (running) - clickable to expand
- ✓ bash (success) - green indicator
- ✗ bash (error) - red indicator

---

## Open Questions

1. **Performance**: Will frequent re-renders of mixed content impact TUI performance?
2. **Scrollback**: How does interleaved content affect scrollback buffer size calculations?
3. **Copy/Paste**: Should copying a message include thinking blocks or just final output?
4. **Session Format**: Should we version the session format for this change?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-25 | Implement for both Web UI and TUI | User requested both interfaces |
| 2026-03-25 | Leverage existing thinking block collapsibility | Thinking blocks already implemented, just need interleaving |
| 2026-03-25 | Remove tool call borders/backgrounds | Cleaner UI, show only button-style element |
| TBD | Use sequence numbers for ordering | Simpler than timestamps, monotonic guarantee |

---

## Dependencies

- **PyPiTUI**: Requires support for dynamic content updates
- **Agent Loop**: Must yield streaming events (may require LLM provider support)

---

## Out of Scope

- Persisting thinking blocks to memory system
- Custom thinking block styling per theme

---

## Notes

- This feature enhances the "streaming first" design principle
- Consider impact on existing `/context` command display
- Ensure accessibility (screen readers) can navigate interleaved content
