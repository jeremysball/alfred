# PRD #91: Inline Streaming Markdown Renderer

**Status**: Draft  
**Priority**: High  
**Author**: Claude (Agent)  
**Created**: 2026-02-22  
**Related PRDs**: #85 (Enhanced CLI Status Line), #89 (Notification System)

---

## Problem Statement

The current CLI uses `rich.live.Live` for streaming markdown, which conflicts with `prompt_toolkit`:

1. **Prompt Overwrites**: Live's background cursor loop conflicts with prompt_toolkit's input handling
2. **Invisible Prompt**: The prompt becomes invisible or gets overwritten during streaming
3. **No Natural Scrollback**: Uses alternate screen buffer, breaking terminal scroll history
4. **Fragile Integration**: Complex workarounds needed to make Live and prompt_toolkit coexist

Users lose their prompt during streaming and can't scroll back through conversation history naturally.

---

## Solution Overview

Build a **custom streaming markdown renderer** that:

1. **Manual ANSI Control**: Uses raw ANSI escape codes for cursor movement
2. **patch_stdout Integration**: Wraps rendering in `prompt_toolkit.patch_stdout` for safe prompt handling
3. **Natural Scrollback**: No alternate screen buffer — output scrolls naturally
4. **Unified Rendering**: Handles all content types (markdown text, tool panels, notifications)
5. **Diff-Based Updates**: Only redraws changed lines for smooth updates

---

## Technical Architecture

### Core Pipeline

```
Stream Chunk → State Update → Render → Diff → Cursor Move → Draw
```

### Component: StreamingRenderer

```python
class StreamingRenderer:
    """Manages inline streaming markdown rendering above prompt_toolkit prompt."""
    
    def __init__(self, console: Console):
        self.full_content: str = ""
        self.previous_lines: list[str] = []
        self.console = console
    
    async def render_stream(self, chunks: AsyncIterator[str]) -> AsyncIterator[str]:
        """Consume chunks, render inline, yield for downstream use."""
        
    def _render_markdown(self, content: str) -> list[str]:
        """Render markdown to list of ANSI-styled lines."""
        
    def _diff_lines(self, old: list[str], new: list[str]) -> int:
        """Find first index where lines diverge."""
        
    def _draw_from_index(self, lines: list[str], start_index: int) -> None:
        """Move cursor, draw lines from diff point, clear orphans."""
```

### The Render Step

```python
def _render_markdown(self, content: str) -> list[str]:
    # Capture rendered markdown to string
    with self.console.capture() as capture:
        self.console.print(Markdown(content))
    output = capture.get()
    
    # Split into lines, preserve ANSI codes
    return output.splitlines()
```

### The Diff & Cursor Math

```python
def _diff_lines(self, old: list[str], new: list[str]) -> int:
    """Find first divergent line index."""
    min_len = min(len(old), len(new))
    for i in range(min_len):
        if old[i] != new[i]:
            return i
    # All shared lines match, diff is at the shorter length
    return min_len
```

### The Draw Step

```python
def _draw_from_index(self, lines: list[str], start_index: int) -> None:
    with patch_stdout():
        # Move cursor UP to diff point
        lines_to_move = len(self.previous_lines) - start_index
        if lines_to_move > 0:
            sys.stdout.write(f"\033[{lines_to_move}A")
        
        # Draw new lines from diff point
        for i, line in enumerate(lines[start_index:], start=start_index):
            sys.stdout.write(f"{line}\033[K\n")  # Line + clear to EOL + newline
        
        # Clear orphan lines if new render is shorter
        orphan_count = len(self.previous_lines) - len(lines)
        for _ in range(orphan_count):
            sys.stdout.write(f"\033[K\n")  # Clear each orphan line
        
        sys.stdout.flush()
    
    self.previous_lines = lines
```

### ANSI Codes Reference

| Code | Meaning |
|------|---------|
| `\033[nA` | Move cursor up n lines |
| `\033[nB` | Move cursor down n lines |
| `\033[K` | Clear from cursor to end of line |
| `\033[J` | Clear from cursor to end of screen |

---

## Component Design

### StreamingRenderer Class

```python
class StreamingRenderer:
    """Inline streaming markdown renderer with prompt_toolkit integration."""
    
    def __init__(
        self,
        console: Console | None = None,
        width: int | None = None,
    ) -> None:
        self.console = console or Console(force_terminal=True, width=width)
        self._content_buffer: str = ""
        self._rendered_lines: list[str] = []
        self._segments: list[RenderSegment] = []  # Track message/tool segments
    
    # === Public API ===
    
    async def render_stream(
        self, 
        chunks: AsyncIterator[str],
    ) -> AsyncIterator[str]:
        """Render streaming content inline. Yields chunks for downstream."""
        
    def add_tool_panel(self, tool_name: str, result: str, is_error: bool) -> None:
        """Add a tool panel to the render output."""
        
    def clear(self) -> None:
        """Clear rendered content for new message."""
        
    def finalize(self) -> None:
        """Ensure final render is complete, reset state."""
    
    # === Private Methods ===
    
    def _render_full(self) -> list[str]:
        """Render all segments (markdown + tool panels) to lines."""
        
    def _draw_diff(self, new_lines: list[str]) -> None:
        """Calculate diff and draw changed lines."""
        
    def _move_cursor_up(self, lines: int) -> None:
        """ANSI cursor movement."""
        
    def _clear_orphans(self, count: int) -> None:
        """Clear orphaned lines at bottom."""
```

### RenderSegment Dataclass

```python
@dataclass
class RenderSegment:
    """A segment of rendered content (text or tool panel)."""
    type: Literal["text", "tool"]
    content: str  # Markdown text or tool result
    tool_name: str | None = None
    is_error: bool = False
```

---

## Integration with CLI

### Refactored CLIInterface

```python
class CLIInterface:
    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console(force_terminal=True)
        self.renderer = StreamingRenderer(console=self.console)
        self.session: PromptSession[str] = PromptSession(...)
    
    async def _stream_response(self, user_input: str) -> None:
        """Stream LLM response using inline renderer."""
        self.renderer.clear()
        
        async for chunk in self.alfred.chat_stream(user_input, tool_callback=self._on_tool):
            # Renderer handles inline updates
            async for _ in self.renderer.render_stream(iter([chunk])):
                pass  # Rendering happens in renderer
        
        self.renderer.finalize()
```

### Tool Panel Rendering

Tool panels are rendered as Rich Panels but captured to ANSI strings:

```python
def _render_tool_panel(self, segment: RenderSegment) -> str:
    """Render a tool panel to ANSI string."""
    panel = Panel(
        self._truncate(segment.content),
        title=f"Tool: {segment.tool_name}",
        border_style="red" if segment.is_error else "dim blue",
    )
    with self.console.capture() as capture:
        self.console.print(panel)
    return capture.get()
```

---

## Edge Cases

### 1. Collapsing Content (Fewer Lines)

When new render has fewer lines than previous:
```python
orphan_count = len(previous_lines) - len(new_lines)
for _ in range(orphan_count):
    sys.stdout.write("\033[K\n")  # Clear each orphan
```

### 2. Empty Content

Handle empty chunks gracefully:
```python
if not chunk and not self._content_buffer:
    return  # Nothing to render
```

### 3. Very Long Lines

Lines wider than terminal wrap automatically via Rich's width handling. Cursor math must account for wrapped lines.

### 4. Rapid Updates (Throttling)

Prevent rendering more frequently than frame rate:
```python
MIN_FRAME_TIME = 0.016  # ~60fps max
last_render = time.time()

if time.time() - last_render < MIN_FRAME_TIME:
    return  # Skip this render
```

### 5. Terminal Resize

Rich handles width changes, but cursor position may drift. Consider re-rendering full content on resize.

---

## Implementation Plan

### Milestone 1: Core Renderer Class

**Goal**: Implement `StreamingRenderer` with basic markdown streaming

**Tasks**:
- Create `src/interfaces/renderer.py` with `StreamingRenderer` class
- Implement `_render_markdown()` using `console.capture()`
- Implement `_diff_lines()` for line comparison
- Implement `_draw_from_index()` with ANSI codes and `patch_stdout`
- Handle orphan line clearing

**Validation**:
- Unit test: Diff detection returns correct index
- Unit test: ANSI output contains expected escape codes
- Manual test: Stream simple markdown, verify inline updates

### Milestone 2: Async Streaming Integration

**Goal**: Integrate renderer with async iterator pattern

**Tasks**:
- Implement `render_stream()` async generator
- Add throttling (max 100ms between renders)
- Handle chunk accumulation
- Implement `finalize()` for clean completion

**Validation**:
- Unit test: Chunks accumulate correctly
- Manual test: Stream multi-chunk message, verify smooth updates
- Performance: Updates complete in <100ms

### Milestone 3: Tool Panel Support

**Goal**: Render tool panels inline with markdown

**Tasks**:
- Add `RenderSegment` dataclass
- Implement `add_tool_panel()` method
- Implement `_render_full()` to combine segments
- Render Rich Panels to ANSI strings
- Handle tool panel visibility toggle (Ctrl-T)

**Validation**:
- Manual test: Tool panels appear inline during streaming
- Manual test: Toggle panels works correctly
- Test: Error panels styled differently

### Milestone 4: CLI Integration

**Goal**: Replace `ConversationBuffer` + `Live` in CLIInterface

**Tasks**:
- Refactor `CLIInterface._stream_response()` to use `StreamingRenderer`
- Remove `ConversationBuffer` class
- Remove Rich `Live` usage
- Wire tool callbacks to `renderer.add_tool_panel()`
- Ensure status line still works (separate from renderer)

**Validation**:
- Manual test: Full conversation flow works
- Manual test: Tool calls appear correctly
- Manual test: Prompt stays visible and functional
- Test: Natural scrollback works in terminal

### Milestone 5: Error Handling & Edge Cases

**Goal**: Handle all edge cases robustly

**Tasks**:
- Handle terminal resize events
- Handle empty/malformed chunks
- Handle very long lines (wrapping)
- Add recovery for cursor drift
- Ensure `sys.stdout.flush()` after ANSI codes

**Validation**:
- Test: Resize terminal during streaming
- Test: Empty chunks don't cause issues
- Test: 1000-char line wraps correctly

### Milestone 6: E2E Testing with tmux-tape

**Goal**: Visual verification of rendering behavior

**Tasks**:
- Create E2E test using tmux-tape
- Test streaming with various content (markdown, code, tables)
- Test tool panel rendering
- Test prompt preservation during streaming
- Capture screenshots for documentation

**Validation**:
- E2E test captures correct visual output
- Screenshots show proper inline rendering

---

## Testing Strategy

### Unit Tests

```python
def test_diff_lines_returns_first_divergence():
    renderer = StreamingRenderer()
    old = ["line 1", "line 2", "line 3"]
    new = ["line 1", "line 2 modified", "line 3"]
    assert renderer._diff_lines(old, new) == 1

def test_render_markdown_produces_ansi():
    renderer = StreamingRenderer()
    lines = renderer._render_markdown("**bold**")
    assert len(lines) > 0
    assert "\033[" in lines[0]  # Contains ANSI codes

def test_clear_orphans_produces_escape_codes():
    renderer = StreamingRenderer()
    # ... setup previous_lines ...
    output = renderer._clear_orphans(3)
    assert "\033[K" in output
```

### E2E Tests (tmux-tape)

```python
async def test_streaming_markdown_inline():
    with TerminalSession("alfred-render", port=7681) as s:
        s.send("alfred")
        s.send_key("Enter")
        s.sleep(3)
        
        s.send("tell me a short story")
        s.send_key("Enter")
        s.sleep(15)  # Wait for streaming
        
        result = s.capture("streaming.png")
        # Verify: Prompt visible at bottom
        # Verify: Markdown rendered above prompt
        assert ">>>" in result["text"]  # Prompt present
```

---

## Success Criteria

1. **Prompt Always Visible**: Prompt never overwritten or invisible during streaming
2. **Natural Scrollback**: Output scrolls naturally in terminal history
3. **Smooth Updates**: Render latency < 100ms per chunk
4. **All Content Types**: Markdown text, tool panels, and notifications render correctly
5. **No Flicker**: Diff-based updates prevent full redraws
6. **Robust Edge Cases**: Resize, empty chunks, long lines handled gracefully

---

## Open Questions

1. **Status Line**: Should the enhanced status line be rendered above or below the markdown? (Current: below, in prompt toolbar)
2. **Notification Integration**: How do PRD #89 notifications interact with this renderer?
3. **Multi-line Input**: How does cursor math handle multi-line user input being edited?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Manual ANSI control + patch_stdout | Live conflicts with prompt_toolkit, need direct control |
| 2026-02-22 | Diff-based rendering | Only redraw changed lines for smooth updates |
| 2026-02-22 | Natural scrollback (no alt screen) | User requirement for terminal history |
| 2026-02-22 | Unified renderer for all content | Simpler than multiple render systems |
| 2026-02-22 | Async iterator input | Fits with existing streaming pattern |
| 2026-02-22 | Main thread (no separate thread) | prompt_toolkit event loop compatibility |

---

## Related Links

- GitHub Issue: #91
- Current Implementation: `src/interfaces/cli.py`
- Related: PRD #85 (Status Line), PRD #89 (Notifications)
- ANSI Codes Reference: https://en.wikipedia.org/wiki/ANSI_escape_code
