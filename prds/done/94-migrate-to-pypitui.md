# PRD: Migrate Alfred CLI to PyPiTUI

**Status**: Draft
**Priority**: Medium
**Created**: 2026-02-25

---

## Problem Statement

Alfred's CLI currently uses a combination of:
- **prompt_toolkit** - Input handling, completion, key bindings
- **rich** - Rendering panels, tables, markdown, live updates

This works but has limitations:
- Two separate libraries with different paradigms
- No scrollback buffer support (content lost when terminal scrolls)
- Complex stdout patching for prompt_toolkit compatibility
- Manual status line management
- No component-based architecture

## Solution Overview

Migrate to **PyPiTUI** - a unified TUI library with:
- Single library for input + rendering
- **Scrollback support** - content flows into terminal's native scrollback
- **Differential rendering** - only updates changed lines
- **Component-based** architecture similar to React
- **Rich integration** - can still use Rich markup
- Synchronized output (DEC 2026) prevents flickering

---

## Current Architecture

```
src/interfaces/cli.py
├── CLIInterface
│   ├── Console (rich)
│   ├── ConversationBuffer (custom)
│   ├── PromptSession (prompt_toolkit)
│   └── Live (rich) for streaming
```

### Key Components

| Current | Purpose |
|---------|---------|
| `prompt_toolkit.PromptSession` | User input with completion |
| `rich.Console` | Output rendering |
| `rich.Live` | Streaming updates |
| `rich.Panel` | Message containers |
| `rich.Table` | Session list display |
| `rich.Markdown` | Message formatting |
| `ConversationBuffer` | Custom segment management |

---

## Target Architecture

```
src/interfaces/pypitui_cli.py
├── AlfredTUI (extends TUI)
│   ├── ConversationView (Component)
│   ├── StatusLine (Component)
│   ├── InputField (Component)
│   └── SessionList (Overlay)
```

### Component Mapping

| Current | PyPiTUI Equivalent |
|---------|-------------------|
| `PromptSession` | `Input` component |
| `Console.print` | `Text` component |
| `Panel` | `BorderedBox` component |
| `Live` streaming | `render_frame()` in loop |
| `Table` | `RichTable` component |
| `Markdown` | `Markdown` component |
| `ConversationBuffer` | Custom `Container` subclass |

---

## Migration Phases

### Phase 1: Foundation
**Goal**: Set up PyPiTUI alongside existing CLI

**Tasks**:
- [ ] Add `pypitui` to dependencies
- [ ] Create `src/interfaces/pypitui_cli.py` skeleton
- [ ] Implement basic TUI with Input + Text components
- [ ] Verify input handling works with async

**Validation**: Basic REPL works with PyPiTUI

---

### Phase 2: Conversation Display
**Goal**: Render conversation history with PyPiTUI

**Tasks**:
- [ ] Create `MessagePanel` component (wraps BorderedBox)
- [ ] Create `ConversationContainer` component
- [ ] Implement message rendering with Rich markdown
- [ ] Add user/assistant styling
- [ ] Port tool call display

**Validation**: Messages display correctly with styling

---

### Phase 3: Streaming Support
**Goal**: Stream LLM responses in real-time

**Tasks**:
- [ ] Implement streaming text update pattern
- [ ] Use differential rendering for smooth updates
- [ ] Handle concurrent input during streaming
- [ ] Test with long responses

**Validation**: Streaming works without flickering

---

### Phase 4: Status Line
**Goal**: Persistent status line above input

**Tasks**:
- [ ] Create `StatusLine` component
- [ ] Display: model, tokens, context, memories
- [ ] Add streaming indicator (spinner)
- [ ] Update in real-time during streaming

**Validation**: Status line updates correctly

---

### Phase 5: Session Management
**Goal**: Session commands and overlay

**Tasks**:
- [ ] Implement `/new`, `/resume`, `/sessions`, `/session` commands
- [ ] Create `SessionListOverlay` component
- [ ] Add tab completion for session IDs
- [ ] Display session history on resume

**Validation**: All session commands work

---

### Phase 6: Advanced Features
**Goal**: Feature parity with current CLI

**Tasks**:
- [ ] Implement `Ctrl-T` toggle for tool panels
- [ ] Add notification display (cron job alerts)
- [ ] Implement `/compact` command
- [ ] Add keyboard shortcuts

**Validation**: Full feature parity

---

### Phase 7: Cleanup
**Goal**: Remove old CLI implementation

**Tasks**:
- [ ] Remove `prompt_toolkit` dependency
- [ ] Remove old `cli.py` or deprecate
- [ ] Update entry points
- [ ] Update documentation

**Validation**: Clean migration, no regressions

---

## Code Examples

### Basic Setup

```python
# src/interfaces/pypitui_cli.py
from pypitui import (
    TUI, Container, Text, Input, BorderedBox,
    ProcessTerminal, OverlayOptions
)
from pypitui.rich_components import Markdown, RichText

class AlfredTUI:
    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.terminal = ProcessTerminal()
        self.tui = TUI(self.terminal)  # Main buffer for scrollback
        
        # Components
        self.conversation = Container()
        self.status_line = StatusLine()
        self.input_field = Input(placeholder="Type a message...")
        
        # Build layout
        self.tui.add_child(self.conversation)
        self.tui.add_child(self.status_line)
        self.tui.add_child(self.input_field)
        self.tui.set_focus(self.input_field)
        
        # Wire input handler
        self.input_field.on_submit = self._on_submit

    async def run(self) -> None:
        self.tui.start()
        try:
            while True:
                data = self.terminal.read_sequence(timeout=0.05)
                if data:
                    self.tui.handle_input(data)
                self.tui.request_render()
                self.tui.render_frame()
                await asyncio.sleep(0.001)  # Yield to event loop
        finally:
            self.tui.stop()

    def _on_submit(self, text: str) -> None:
        # Handle user input
        self.input_field.set_value("")  # Clear input
        # Add to conversation, trigger LLM, etc.
```

### Streaming Pattern

```python
async def _stream_response(self, user_input: str) -> None:
    """Stream LLM response with real-time updates."""
    # Add user message
    self._add_message("user", user_input)
    
    # Create assistant message container
    assistant_msg = BorderedBox(title="Alfred", padding_x=1)
    self.conversation.add_child(assistant_msg)
    
    # Stream response
    current_text = ""
    async for chunk in self.alfred.chat_stream(user_input):
        current_text += chunk
        # Update the message content
        assistant_msg.clear_children()
        assistant_msg.add_child(Markdown(current_text))
        self.tui.request_render()
```

### Status Line Component

```python
class StatusLine(Component):
    def __init__(self, get_status: Callable[[], StatusData]) -> None:
        self._get_status = get_status
        self._is_streaming = False
        
    def render(self, width: int) -> list[str]:
        status = self._get_status()
        
        # Build status text
        parts = [
            f"[bold]{status.model_name}[/]",
            f"in:{self._fmt(status.usage.input_tokens)}",
            f"out:{self._fmt(status.usage.output_tokens)}",
            f"📚 {status.memories_count}",
            f"💬 {status.session_messages}",
        ]
        
        if self._is_streaming:
            parts.insert(0, "⠋")  # Spinner (would need animation)
        
        text = " | ".join(parts)
        return [RichText(f"[on color(236)] {text} [/]").render(width)[0]]
```

### Session List Overlay

```python
def show_session_list(self) -> None:
    """Show session list as overlay."""
    sessions = self.alfred.session_manager.list_sessions()
    
    # Create session list content
    content = Container()
    for meta in sessions:
        item = Text(f"{meta.session_id} - {meta.message_count} msgs")
        content.add_child(item)
    
    # Show as centered overlay
    self.tui.show_overlay(
        BorderedBox(title="Sessions", children=[content]),
        OverlayOptions(width=60, anchor="center")
    )
```

---

## Key Differences

| Aspect | Current (prompt_toolkit + rich) | PyPiTUI |
|--------|--------------------------------|---------|
| Input | `PromptSession` async | `Input` component + manual loop |
| Rendering | `Console.print()` | Component `render()` |
| Streaming | `Live` context manager | `render_frame()` in loop |
| Scrollback | Content lost | Flows to scrollback buffer |
| Overlays | Manual positioning | Built-in overlay system |
| Architecture | Imperative | Component-based |

---

## Benefits

1. **Scrollback Support** - Users can scroll back through conversation history with Shift+PgUp
2. **Unified Library** - Single dependency instead of two
3. **Differential Rendering** - Only changed lines update (less flickering)
4. **Component Architecture** - Easier to reason about UI structure
5. **Rich Integration** - Can still use Rich markup via `rich_components`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Async compatibility issues | Medium | High | Test early with async loop |
| Missing prompt_toolkit features | Low | Medium | PyPiTUI has Input component |
| Rich rendering differences | Low | Low | PyPiTUI wraps Rich |
| Learning curve | Medium | Low | Follow demo patterns |

---

## Dependencies

- PyPiTUI: `pip install pypitui`
- Optional Rich support: `pip install pypitui[rich]`

---

## References

- [PyPiTUI Repository](https://github.com/jeremysball/pypitui)
- [PyPiTUI Demo](https://github.com/jeremysball/pypitui/blob/main/examples/demo.py)
- [PyPiTUI README](https://github.com/jeremysball/pypitui#readme)
- Current implementation: `src/interfaces/cli.py`

---

## Success Criteria

- [ ] All current CLI features work with PyPiTUI
- [ ] Streaming works without flickering
- [ ] Conversation history accessible via scrollback
- [ ] Input handling is responsive
- [ ] Status line updates in real-time
- [ ] Session management commands work
- [ ] No regressions in functionality
