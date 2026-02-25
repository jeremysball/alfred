# PyPiTUI Migration Implementation Guide

This guide provides concrete code examples for migrating Alfred's CLI from prompt_toolkit + rich to PyPiTUI.

## Quick Reference

### Current vs PyPiTUI

```python
# CURRENT: prompt_toolkit + rich
from prompt_toolkit import PromptSession
from rich.console import Console
from rich.live import Live

console = Console()
session = PromptSession(message=">>> ")

with Live(console=console) as live:
    live.update(panel)

user_input = await session.prompt_async()
```

```python
# NEW: PyPiTUI
from pypitui import TUI, Input, Text, ProcessTerminal

terminal = ProcessTerminal()
tui = TUI(terminal)

input_field = Input(placeholder=">>> ")
tui.add_child(input_field)
tui.set_focus(input_field)

tui.render_frame()
```

---

## Step 1: Basic Setup

### Create the TUI Instance

```python
# src/interfaces/pypitui_cli.py

from pypitui import (
    TUI, Container, Text, Input, BorderedBox, Spacer,
    OverlayOptions, ProcessTerminal
)
from pypitui.rich_components import Markdown, RichText

class AlfredTUI:
    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.terminal = ProcessTerminal()
        self.tui = TUI(self.terminal)  # Main buffer mode for scrollback
        
        # UI components
        self.conversation = Container()
        self.status_line = Text("", padding_y=0)
        self.input_field = Input(placeholder="Type your message...")
        
        # Wire up input
        self.input_field.on_submit = self._on_submit
        
        # Build initial layout
        self._build_layout()
    
    def _build_layout(self) -> None:
        """Build the initial UI layout."""
        self.tui.clear()
        
        # Header
        header = BorderedBox(title="Alfred", padding_x=2)
        header.add_child(Text("Persistent Memory Assistant", padding_y=0))
        self.tui.add_child(header)
        self.tui.add_child(Spacer(1))
        
        # Conversation area (will grow into scrollback)
        self.tui.add_child(self.conversation)
        self.tui.add_child(Spacer(1))
        
        # Status line
        self.tui.add_child(self.status_line)
        
        # Input
        self.tui.add_child(self.input_field)
        self.tui.set_focus(self.input_field)
```

---

## Step 2: Conversation Display

### Replace ConversationBuffer

```python
# CURRENT: ConversationBuffer with segments
class ConversationBuffer:
    def __init__(self):
        self.segments: list[Segment] = []
    
    def add_text(self, chunk: str, role: str):
        self._current_text += chunk
    
    def render(self) -> list[RenderableType]:
        # Complex panel rendering...
```

```python
# NEW: Simple Container with BorderedBox children
class ConversationView(Container):
    """Container for conversation messages."""
    
    def add_message(self, content: str, role: str = "assistant") -> None:
        """Add a message to the conversation."""
        border_style = "cyan" if role == "user" else "green"
        title = "You" if role == "user" else "Alfred"
        
        box = BorderedBox(
            padding_x=1,
            padding_y=0,
            title=title,
        )
        # Use Markdown component for Rich rendering
        box.add_child(Markdown(content))
        self.add_child(box)
    
    def add_tool_result(self, tool_name: str, result: str, is_error: bool) -> None:
        """Add a tool result panel."""
        style = "red" if is_error else "blue"
        truncated = result[:500] + "..." if len(result) > 500 else result
        
        box = BorderedBox(padding_x=1, title=f"Tool: {tool_name}")
        box.add_child(Text(truncated, padding_y=0))
        self.add_child(box)
```

---

## Step 3: Streaming Updates

### Replace Live with render_frame()

```python
# CURRENT: rich.Live for streaming
with Live(console=self.console, refresh_per_second=12) as live:
    async for chunk in self.alfred.chat_stream(user_input):
        self.buffer.add_text(chunk)
        live.update(self.buffer.render())
```

```python
# NEW: render_frame() in async loop
async def _stream_response(self, user_input: str) -> None:
    """Stream LLM response with real-time updates."""
    current_text = ""
    message_box = None
    
    async for chunk in self.alfred.chat_stream(user_input):
        current_text += chunk
        
        # Update or create the message box
        if message_box is None:
            message_box = BorderedBox(title="Alfred", padding_x=1)
            self.conversation.add_child(message_box)
        
        # Clear and re-add content
        message_box.clear()
        message_box.add_child(Markdown(current_text))
        
        # Request render
        self.tui.request_render()
        self.tui.render_frame()
        
        # Small delay to allow input processing
        await asyncio.sleep(0.01)
```

---

## Step 4: Input Handling

### Replace PromptSession with Input component

```python
# CURRENT: prompt_toolkit async prompt
try:
    with self._patch_stdout_with_status():
        user_input = await self.session.prompt_async()
except EOFError:
    return
except KeyboardInterrupt:
    self.console.print("Goodbye!")
    return
```

```python
# NEW: Main loop with input handling
async def run(self) -> None:
    """Main event loop."""
    self.tui.start()
    
    try:
        while True:
            # Check for input
            data = self.terminal.read_sequence(timeout=0.01)
            if data:
                self.tui.handle_input(data)
            
            # Render frame
            self.tui.request_render()
            self.tui.render_frame()
            
            # Small delay
            await asyncio.sleep(0.016)  # ~60fps
    finally:
        self.tui.stop()

def _on_submit(self, text: str) -> None:
    """Handle input submission."""
    if not text.strip():
        return
    
    if text.lower() == "exit":
        self.running = False
        return
    
    # Add user message to conversation
    self.conversation.add_message(text, role="user")
    
    # Clear input
    self.input_field.set_value("")
    
    # Start streaming response
    asyncio.create_task(self._stream_response(text))
```

---

## Step 5: Status Line

### Replace custom status rendering

```python
# CURRENT: Custom _render_status_line with Rich
def _render_status_line(self) -> RenderableType:
    text = Text()
    text.append(self.model_name, style="bold white")
    text.append(f" | in:{usage.input_tokens}")
    # ... complex formatting
    return text
```

```python
# NEW: StatusLine component
class StatusLine(Container):
    """Status bar showing model info and token usage."""
    
    def __init__(self) -> None:
        super().__init__()
        self._text = Text("", padding_y=0)
        self.add_child(self._text)
    
    def update(self, model: str, usage: TokenUsage, memories: int, 
               session_msgs: int) -> None:
        """Update status line content."""
        # Build status string
        parts = [
            f"[bold]{model}[/bold]",
            f"in:{self._format(usage.input_tokens)}",
            f"out:{self._format(usage.output_tokens)}",
        ]
        if usage.cache_read_tokens > 0:
            parts.append(f"cache:{self._format(usage.cache_read_tokens)}")
        
        parts.append(f"📚 {memories}")
        parts.append(f"💬 {session_msgs}")
        
        # Use RichText for formatting
        self._text.set_rich_text(" | ".join(parts))
    
    @staticmethod
    def _format(n: int) -> str:
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)
```

---

## Step 6: Session Commands

### Handle commands in input callback

```python
def _on_submit(self, text: str) -> None:
    """Handle input submission."""
    text = text.strip()
    
    # Session commands
    if text.startswith("/"):
        self._handle_command(text)
        return
    
    if text.lower() == "exit":
        self.running = False
        return
    
    # Normal chat
    self.conversation.add_message(text, role="user")
    self.input_field.set_value("")
    asyncio.create_task(self._stream_response(text))

def _handle_command(self, cmd: str) -> None:
    """Handle session commands."""
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None
    
    if command == "/new":
        self.alfred.session_manager.new_session()
        self.conversation.clear()
        self._show_toast("New session created")
    
    elif command == "/sessions":
        self._show_session_list()
    
    elif command == "/resume" and arg:
        self._resume_session(arg)

def _show_session_list(self) -> None:
    """Show session list as overlay."""
    sessions = self.alfred.session_manager.list_sessions()
    
    content = Container()
    for meta in sessions:
        line = f"{meta.session_id} - {meta.message_count} msgs"
        content.add_child(Text(line, padding_y=0))
    
    box = BorderedBox(title="Sessions", padding_x=1)
    box.add_child(content)
    
    self.tui.show_overlay(box, OverlayOptions(width=50, anchor="center"))

def _show_toast(self, message: str) -> None:
    """Show temporary toast message."""
    toast = BorderedBox(padding_x=2)
    toast.add_child(RichText(f"[green]{message}[/green]"))
    
    handle = self.tui.show_overlay(
        toast, 
        OverlayOptions(anchor="bottom", offset_y=2)
    )
    
    # Auto-hide after 2 seconds
    async def hide():
        await asyncio.sleep(2)
        handle.hide()
    
    asyncio.create_task(hide())
```

---

## Step 7: Main Loop Integration

### Full async main loop

```python
async def run(self) -> None:
    """Main event loop with input handling and rendering."""
    self.tui.start()
    self.running = True
    
    try:
        while self.running:
            # Process input
            data = self.terminal.read_sequence(timeout=0.001)
            if data:
                self.tui.handle_input(data)
            
            # Update status line
            self.status_line.update(
                model=self.alfred.model_name,
                usage=self.alfred.token_tracker.usage,
                memories=self.alfred.context_summary.memories_count,
                session_msgs=self.alfred.context_summary.session_messages,
            )
            
            # Render
            self.tui.request_render()
            self.tui.render_frame()
            
            # Yield to event loop
            await asyncio.sleep(0.016)  # ~60fps
    
    finally:
        self.tui.stop()
```

---

## Migration Checklist

- [ ] Add `pypitui` to `pyproject.toml` dependencies
- [ ] Create `src/interfaces/pypitui_cli.py`
- [ ] Implement `AlfredTUI` class
- [ ] Implement `ConversationView` component
- [ ] Implement `StatusLine` component  
- [ ] Wire up input handling
- [ ] Port streaming logic
- [ ] Port session commands
- [ ] Port overlay system
- [ ] Test all features
- [ ] Remove old `cli.py`
- [ ] Update imports in `cli/main.py`

---

## Testing

```bash
# Install pypitui
pip install pypitui[rich]

# Run Alfred with new interface
alfred

# Test features:
# - Type messages, verify streaming works
# - Press Shift+PgUp to see scrollback
# - Run /sessions command
# - Run /new command
# - Run /resume <id>
# - Test exit command
```
