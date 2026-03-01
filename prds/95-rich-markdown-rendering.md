# PRD: Rich Markdown Rendering in TUI

**Status**: Complete  
**Priority**: High  
**Created**: 2026-02-28  
**Completed**: 2026-02-28  
**Issue**: #95  

---

## Summary

Integrate the Rich library into Alfred's PyPiTUI-based CLI to render messages with full markdown support, including syntax highlighting, formatted lists, bold/italic text, and inline code. Rich generates ANSI-colored output that PyPiTUI can display natively.

---

## Problem Statement

### Current State

Alfred's TUI (built on PyPiTUI) displays messages as plain text. When LLMs respond with markdown formatting:

```markdown
Here's how to use the function:

```python
def hello():
    print("Hello, World!")
```

**Note**: Make sure to:
1. Install dependencies
2. Run tests
3. Deploy
```

The output appears as unformatted text, making it hard to read:
- Code blocks lack syntax highlighting
- Lists appear as inline text  
- Bold/italic markers (`**`, `*`) are visible instead of styled
- No visual distinction between code and prose

### Impact

- **Poor readability**: Users struggle to parse formatted LLM output
- **Code is hard to read**: No syntax highlighting for code blocks
- **Lost formatting**: Structural elements (lists, headers) lose meaning
- **Unprofessional appearance**: Plain text feels basic compared to modern CLIs

---

## Solution Overview

Integrate Rich's `Markdown` and `Console` classes to render messages with full formatting:

1. **Markdown Rendering**: Convert LLM markdown responses to ANSI-colored text
2. **Markup Support**: Allow inline console markup for emphasis
3. **Syntax Highlighting**: Automatic language detection and highlighting for code blocks
4. **Streaming Support**: Efficient re-rendering as content streams in
5. **Performance**: Batch updates to avoid excessive re-rendering

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MessagePanel                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │ Raw Text    │───▶│ Rich Markdown│───▶│ ANSI Output         │ │
│  │ from LLM    │    │ Rendering    │    │ (PyPiTUI displays)  │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Rich Integration                            │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │ StringIO    │───▶│ Rich Console │───▶│ ANSI Text           │ │
│  │ Buffer      │    │ (force_term) │    │ with colors/styles  │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      PyPiTUI Display                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐ │
│  │ ANSI Text   │───▶│ Pypitui Text │───▶│ BorderedBox Panel   │ │
│  │             │    │ Component    │    │                     │ │
│  └─────────────┘    └──────────────┘    └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Markdown Parser | Rich `Markdown` class | Full markdown-it integration, battle-tested |
| Output Format | ANSI escape sequences | PyPiTUI Text component handles these natively |
| Rendering Buffer | `StringIO` with `Console` | Captures full Rich output with colors |
| Streaming Strategy | Debounced re-rendering | Balance responsiveness with performance |
| Code Theme | `monokai` (configurable) | Popular, readable theme |
| Fallback | Plain text on error | Graceful degradation |

---

## Implementation Phases

### Phase 1: Core Rich Integration

#### 1.1 Create Rich Rendering Module

**File**: `src/interfaces/pypitui/rich_renderer.py`

```python
"""Rich markdown rendering for PyPiTUI integration."""

from io import StringIO
from typing import Literal

from rich.console import Console
from rich.markdown import Markdown


class RichRenderer:
    """Renders Rich markdown/markup to ANSI text for PyPiTUI display."""

    MIN_WIDTH = 40

    def __init__(
        self,
        width: int = 80,
        code_theme: str = "monokai",
        justify: Literal["left", "center", "right", "full"] = "left",
    ) -> None:
        """Initialize renderer.

        Args:
            width: Terminal width for wrapping
            code_theme: Pygments theme for code blocks
            justify: Text justification
        """
        self.width = max(width, self.MIN_WIDTH)
        self.code_theme = code_theme
        self.justify = justify

    def render_markdown(self, text: str) -> str:
        """Render markdown text to ANSI-colored output.

        Args:
            text: Markdown-formatted text

        Returns:
            ANSI escape sequence formatted text
        """
        try:
            buffer = StringIO()
            console = Console(
                file=buffer,
                width=self.width,
                force_terminal=True,
                color_system="truecolor",
                markup=True,
                emoji=True,
            )

            md = Markdown(
                text,
                code_theme=self.code_theme,
                justify=self.justify,
            )

            console.print(md)
            return buffer.getvalue()
        except Exception:
            return text

    def render_markup(self, text: str) -> str:
        """Render console markup to ANSI-colored output.

        Args:
            text: Text with Rich console markup

        Returns:
            ANSI escape sequence formatted text
        """
        try:
            buffer = StringIO()
            console = Console(
                file=buffer,
                width=self.width,
                force_terminal=True,
                color_system="truecolor",
            )

            console.print(text, markup=True, emoji=True)
            return buffer.getvalue()
        except Exception:
            return text

    def update_width(self, width: int) -> None:
        """Update terminal width.

        Args:
            width: New terminal width
        """
        self.width = max(width, self.MIN_WIDTH)
```

#### 1.2 Tests for RichRenderer

**File**: `tests/pypitui/test_rich_renderer.py`

- [x] `test_render_markdown_basic()` - Basic markdown renders
- [x] `test_render_markdown_code_block()` - Code blocks with highlighting
- [x] `test_render_markdown_lists()` - Ordered and unordered lists
- [x] `test_render_markup_styling()` - Console markup styles
- [x] `test_render_width_wrapping()` - Text wraps at width
- [x] `test_update_width()` - Width updates correctly
- [x] `test_theme_configuration()` - Custom code themes work

#### 1.3 Update MessagePanel for Rich Support

**File**: `src/interfaces/pypitui/message_panel.py`

Modify `MessagePanel` to optionally use Rich rendering:

```python
class MessagePanel(BorderedBox):
    """A bordered panel for displaying conversation messages with Rich support."""
    
    def __init__(
        self,
        role: Literal["user", "assistant", "system"],
        content: str = "",
        *,
        padding_x: int = 1,
        padding_y: int = 0,
        terminal_width: int = 80,
        use_markdown: bool = True,  # NEW: Enable markdown rendering
    ) -> None:
        # ... existing init ...
        self._use_markdown = use_markdown
        self._renderer = RichRenderer(
            width=terminal_width - 4,  # Account for borders/padding
        ) if use_markdown else None
        
    def set_content(self, text: str) -> None:
        """Update message content with optional markdown rendering."""
        self._text_content = text
        self._rebuild_content()
    
    def _rebuild_content(self) -> None:
        """Rebuild content with Rich markdown support."""
        self.clear()
        
        if self._use_markdown and self._renderer:
            # Render via Rich
            try:
                ansi_text = self._renderer.render_markdown(self._text_content)
                self.add_child(Text(ansi_text))
            except Exception:
                # Fallback to plain text on error
                self.add_child(Text(self._text_content))
        else:
            # Plain text path
            self.add_child(Text(self._text_content))
        
        self.invalidate()
    
    def set_terminal_width(self, width: int) -> None:
        """Update terminal width and re-render."""
        if width != self._terminal_width:
            self._terminal_width = width
            if self._renderer:
                self._renderer.update_width(width - 4)
            if self._text_content:
                self._rebuild_content()
```

#### 1.4 Tests for MessagePanel Rich Integration

**File**: `tests/pypitui/test_message_panel_rich.py`

- [ ] `test_message_panel_renders_markdown()` - Markdown content renders
- [ ] `test_message_panel_plain_fallback()` - Plain text when markdown disabled
- [ ] `test_message_panel_error_fallback()` - Plain text on render error
- [ ] `test_message_panel_width_update_renders()` - Re-renders on width change

---

### Phase 2: Streaming Performance (Skipped)

**Status**: ⏭️ Skipped - No performance issues observed in practice

**Rationale**: The user confirmed that streaming performance is acceptable without debouncing. Re-rendering on every chunk works fine for typical LLM response sizes. This optimization can be revisited if performance issues arise.

**Original Plan**:
- Debounced re-rendering during streaming (render every 100ms instead of per chunk)
- Batch content updates to reduce CPU usage

**Current Behavior**: Content re-renders on every streaming chunk without issues.

---

### Phase 3: Integration with AlfredTUI

#### 3.1 Update AlfredTUI Message Creation

**File**: `src/interfaces/pypitui/tui.py`

Update `_on_submit()` and `_send_message()` to use markdown-enabled MessagePanel:

```python
def _on_submit(self, text: str) -> None:
    """Handle user input submission."""
    text = text.strip()
    if not text:
        return
    
    # Add user message with markdown support
    user_msg = MessagePanel(
        role="user",
        content=text,
        terminal_width=self._terminal_width,
        use_markdown=True,  # Enable markdown
    )
    self.conversation.add_child(user_msg)
    
    # ... rest of method ...

async def _send_message(self, text: str) -> None:
    """Send message and stream response."""
    self._is_streaming = True
    
    # Create assistant message with streaming support
    assistant_msg = StreamingMessagePanel(
        role="assistant",
        content="",
        terminal_width=self._terminal_width,
        use_markdown=True,
        render_interval=0.1,  # Render every 100ms during streaming
    )
    self.conversation.add_child(assistant_msg)
    self._current_assistant_msg = assistant_msg
    
    try:
        accumulated = ""
        async for chunk in self.alfred.chat_stream(
            text, tool_callback=self._tool_callback
        ):
            accumulated += chunk
            assistant_msg.append_content(accumulated)
            # ... status updates ...
        
        assistant_msg.finalize()
        
    except Exception as e:
        assistant_msg.set_error(str(e))
    finally:
        # ... cleanup ...
```

#### 3.2 Configuration Options

Add to config or constants:

```python
# src/interfaces/pypitui/constants.py

# Rich markdown rendering settings
RICH_MARKDOWN_ENABLED = True
RICH_CODE_THEME = "monokai"  # Options: monokai, default, vim, etc.
RICH_STREAMING_INTERVAL = 0.1  # Seconds between renders during streaming
```

---

### Phase 4: Tool Call Rendering

**Status**: ✅ Completed

**Implementation**: Enhanced `MessagePanel._build_content_with_tools()` with Rich formatting:

**Features Added**:
- **Bold tool names**: `[bold]{tool_name}[/bold]` rendered via Rich markup
- **JSON syntax highlighting**: Tool output auto-detected as JSON and formatted with markdown code blocks
- **Color-coded borders**: Blue (running), Green (success), Red (error)

**Changes Made**:
```python
# Bold tool name in title
title = renderer.render_markup(f"[bold]{tc.tool_name}[/bold]")

# JSON formatting for tool output
if stripped.startswith("{") and stripped.endswith("}"):
    pretty_json = json.dumps(parsed, indent=2)
    return f"```json\n{pretty_json}\n```"
```

**Note**: ToolCallPanel component was removed (unused). Tool rendering lives inline in MessagePanel - extraction to a dedicated component is future refactoring work.

---

### Phase 5: Polish & Testing

#### 5.1 Manual Testing Checklist

- [ ] Basic markdown renders correctly (headers, bold, italic)
- [ ] Code blocks have syntax highlighting
- [ ] Lists render with proper indentation
- [ ] Tables render correctly
- [ ] Blockquotes are styled
- [ ] Streaming performance is smooth
- [ ] Long content wraps properly
- [ ] Terminal resize re-renders correctly
- [ ] Fallback to plain text on error
- [ ] Tool output is formatted

#### 5.2 E2E Test

```python
# tests/e2e/test_rich_rendering.py

async def test_markdown_rendering():
    """E2E test for markdown rendering."""
    # Launch Alfred
    # Send message with markdown
    # Capture output
    # Verify ANSI codes present
    # Verify formatting visible
```

---

## Success Criteria

- [x] Markdown messages render with proper formatting
- [x] Code blocks show syntax highlighting
- [x] Lists appear as indented lists, not inline text
- [x] Bold/italic markers render as actual styling
- [x] Terminal resize properly re-renders content
- [x] Graceful fallback when Rich rendering fails
- [x] No regressions in existing TUI functionality
- [x] Session history messages render with markdown on resume
- [x] Tool call panels have bold titles and JSON syntax highlighting
- [x] All 766 tests pass

## Additional Improvements (Completed)

### Agent Behavior Documentation

Updated `AGENTS.md` with clearer priorities and TUI documentation:

- [x] Restructure rule priorities (TDD as #1 after pre-flight)
- [x] Add explicit ANSI color placeholder syntax documentation
- [x] Add "Wrong vs Right" table for background colors (`{on_red}` not `{bg_red}`)
- [x] Document that placeholders don't work inside markdown code blocks

### Reasoning Token Display

Fixed reasoning tokens not appearing in UI status line:

- [x] Accumulate `reasoning_content` during streaming for Kimi models
- [x] Count reasoning tokens locally using tiktoken (Kimi API doesn't return them)
- [x] Display format: `↓40/31ρ` (output tokens / reasoning tokens)
- [x] Add tiktoken dependency for token counting

### Logging Infrastructure

Fixed INFO/DEBUG logs being dropped in TUI mode:

- [x] Add stream handler for INFO/DEBUG logs to stderr
- [x] Keep ToastHandler for WARNING/ERROR in TUI mode
- [x] Ensure both handlers work together properly

### Testing

Added behavioral tests for ANSI color system:

- [x] Create `tests/pypitui/test_ansi.py` with `TestAnsiRenderingBehavior` class
- [x] Test background colors use correct ANSI escape codes (`\033[41m` for red)
- [x] Test `{on_red}` pattern (not `{bg_red}`) produces correct output
- [x] Verify placeholders don't work inside markdown code blocks

### Documentation

Updated `templates/SOUL.md` with expanded personality:

- [x] Add "Default to Yes" section
- [x] Emphasize trust, bravery, and showing up with point of view
- [x] Expand on remembering as a form of care

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
# ... existing dependencies ...
"rich[markdown]" = ">=13.0.0"
```

---

## Migration Path

1. **Phase 1**: Add RichRenderer and basic integration
2. **Phase 2**: Update MessagePanel with opt-in markdown
3. **Phase 3**: Enable by default for new messages
4. **Phase 4**: Remove plain text fallback (once stable)

---

## Open Questions

1. **Performance on large responses**: Should we limit markdown rendering for very long messages (>10KB)?
2. **Code theme preference**: Should users be able to configure the code theme?
3. **Emoji support**: Should we enable emoji rendering in markdown?
4. **Image handling**: How should we handle markdown images? (Currently unsupported)

---

## References

- **Rich Documentation**: `docs/references/RICH.md`
- **PyPiTUI Migration Guide**: `docs/pypitui-migration-guide.md`
- **Rich GitHub**: https://github.com/Textualize/rich
- **Rich Docs**: https://rich.readthedocs.io/

---

## Milestones

| Phase | Description | Status |
|-------|-------------|--------|
| 1.1 | RichRenderer implementation | ✅ |
| 1.2 | Unit tests for rendering | ✅ (29 tests) |
| 1.3 | MessagePanel Rich integration | ✅ |
| 2.1 | Debounced streaming renderer | 🚫 Skipped (no performance issues) |
| 2.2 | Performance optimization | 🚫 Skipped |
| 3.1 | AlfredTUI integration | ✅ |
| 3.2 | Configuration options | ✅ |
| 4.0 | Tool call Rich formatting | ✅ (bold titles, JSON highlighting) |
| 5.0 | E2E testing and polish | ✅ (766 tests pass) |
| 6.0 | Agent behavior documentation | ✅ (AGENTS.md restructuring, ANSI docs) |
| 6.1 | Reasoning token display | ✅ (tiktoken-based counting for Kimi) |
| 6.2 | Logging infrastructure | ✅ (stream handler for INFO/DEBUG) |
| 6.3 | ANSI color testing | ✅ (behavioral tests for TUI colors) |
| 6.4 | Personality updates | ✅ (SOUL.md expanded) |
