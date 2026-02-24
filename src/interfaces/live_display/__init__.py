"""Rich Live display with custom prompt input and mouse scroll support."""

import asyncio
import signal
import sys
import termios
from collections.abc import Callable

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from src.theme import Theme

from .completer import Completer
from .history import History
from .input import InputReader, KeyAction, PromptInput

# Mouse action codes (SGR extended mode)
MOUSE_SCROLL_UP = 64
MOUSE_SCROLL_DOWN = 65


class LiveDisplay:
    """Rich Live display with fixed prompt and status at bottom.

    Layout: content (flexible) | live area (streaming + prompt + status)
    Supports mouse scroll for custom scrollback.
    """

    def __init__(
        self,
        console: Console | None = None,
        history_path: str | None = None,
        get_session_ids: Callable[[], list[str]] | None = None,
        on_scroll: Callable[[int], None] | None = None,
    ) -> None:
        """Initialize LiveDisplay.

        Args:
            console: Console instance
            history_path: Path to history file
            get_session_ids: Callback to get session IDs for completion
            on_scroll: Callback for scroll events (positive = scroll up, negative = scroll down)
        """
        self.console = console or Console()
        self.prompt = PromptInput()
        self.history = History(history_path)
        self.reader = InputReader()
        self.completer = Completer(get_session_ids=get_session_ids)
        self.on_scroll = on_scroll
        self._live: Live | None = None
        self._status: RenderableType = Text("Ready", style=Theme.text_secondary)
        self._history: RenderableType = Text()
        self._streaming: RenderableType | None = None
        self._mouse_enabled = False

        # Create layout: content (flexible) | live (fixed at bottom)
        self._layout = Layout()
        self._layout.split_column(
            Layout(name="content", ratio=1),
            Layout(name="live", size=2),
        )

    def set_status(self, status: RenderableType) -> None:
        """Update status line."""
        self._status = status
        self._refresh()

    def set_history(self, history: RenderableType) -> None:
        """Update the history content (completed messages)."""
        self._history = history
        self._refresh()

    def set_streaming(self, streaming: RenderableType) -> None:
        """Set the currently streaming message."""
        self._streaming = streaming
        self._refresh()

    def clear_streaming(self) -> None:
        """Clear and hide the streaming area."""
        self._streaming = None
        self._refresh()

    def _render(self) -> RenderableType:
        """Render full layout: content (history|streaming) | live."""
        # Build content: history + streaming
        if self._streaming is not None:
            content: RenderableType = Group(self._history, self._streaming)
        else:
            content = self._history

        self._layout["content"].update(content)

        # Live area: prompt + status fixed at bottom
        parts: list[RenderableType] = []
        if self.completer.visible:
            parts.append(self.completer.render_dropdown())
        parts.append(self.prompt.render())
        parts.append(self._status)

        self._layout["live"].update(Group(*parts))

        return self._layout

    def _refresh(self) -> None:
        """Refresh Live display if active."""
        if self._live is not None:
            self._live.update(self._render())

    def start(self) -> None:
        """Start Live display with mouse tracking."""
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=10,
            screen=True,  # Alternate screen for clean UX
            vertical_overflow="visible",  # Allow content to extend into scrollback
        )
        self._live.start()
        self._enable_mouse()
        self._setup_resize_handler()

    def _enable_mouse(self) -> None:
        """Enable SGR extended mouse mode for scroll tracking."""
        if not sys.stdin.isatty():
            return
        # Enable SGR extended mouse mode (1006) with scroll reporting
        sys.stdout.write('\x1b[?1006h\x1b[?1000h')
        sys.stdout.flush()
        self._mouse_enabled = True

    def _disable_mouse(self) -> None:
        """Disable mouse mode."""
        if not sys.stdin.isatty() or not self._mouse_enabled:
            return
        sys.stdout.write('\x1b[?1000l\x1b[?1006l')
        sys.stdout.flush()
        self._mouse_enabled = False

    def _setup_resize_handler(self) -> None:
        """Setup handler for terminal resize events."""
        if sys.stdin.isatty():
            self._original_sigwinch = signal.signal(signal.SIGWINCH, self._on_resize)

    def _on_resize(self, signum: int, frame: object) -> None:
        """Handle terminal resize - force a refresh."""
        self._refresh()

    def stop(self) -> None:
        """Stop Live display."""
        self._disable_mouse()
        if self._live is not None:
            self._live.stop()
            self._live = None
        if hasattr(self, '_original_sigwinch'):
            signal.signal(signal.SIGWINCH, self._original_sigwinch)

    def update(self) -> None:
        """Force refresh of Live display."""
        self._refresh()

    def __enter__(self) -> "LiveDisplay":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    def disable_echo(self) -> None:
        """Disable terminal echo."""
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._original_tty_settings = termios.tcgetattr(fd)
        new_settings = termios.tcgetattr(fd)
        new_settings[3] = new_settings[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, new_settings)

    def enable_echo(self) -> None:
        """Re-enable terminal echo."""
        if not sys.stdin.isatty() or not hasattr(self, '_original_tty_settings'):
            return
        fd = sys.stdin.fileno()
        termios.tcsetattr(fd, termios.TCSANOW, self._original_tty_settings)

    def read_line(self) -> str:
        """Read a line of input with editing support."""
        self.prompt.clear()
        self._refresh()

        while True:
            action, char = self.reader.read()
            if self._handle_action(action, char):
                result = self.prompt.buffer
                self.history.add(result)
                self.completer.hide()
                self.prompt.clear()
                self._refresh()
                return result

    async def read_line_async(self) -> str:
        """Read a line of input with editing support (async)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read_line)

    def _handle_action(self, action: KeyAction, char: str) -> bool:
        """Handle a key action. Returns True if input should be submitted."""
        if self.completer.visible:
            if action in (KeyAction.TAB, KeyAction.DOWN):
                self.completer.next()
                self._refresh()
                return False
            elif action in (KeyAction.SHIFT_TAB, KeyAction.UP):
                self.completer.prev()
                self._refresh()
                return False
            elif action == KeyAction.ENTER:
                selected = self.completer.get_selected()
                if selected:
                    self._apply_completion(selected)
                    self.completer.hide()
                self._refresh()
                return False
            elif action == KeyAction.ESC:
                self.completer.hide()
                self._refresh()
                return False

        if action == KeyAction.INSERT:
            self.prompt.insert(char)
            is_command = (
                self.prompt.buffer.startswith("/")
                and len(self.prompt.buffer) >= 2
                and not self.prompt.buffer[1:].startswith(" ")
            )
            if is_command:
                self.completer.start(self.prompt.buffer)
            else:
                self.completer.hide()
        elif action == KeyAction.SHIFT_ENTER:
            self.prompt.insert("\n")
            self.completer.hide()
        elif action == KeyAction.BACKSPACE:
            self.prompt.delete_left()
            self.completer.hide()
        elif action == KeyAction.DELETE:
            self.prompt.delete_right()
        elif action == KeyAction.DELETE_TO_END:
            self.prompt.delete_to_end()
        elif action == KeyAction.DELETE_TO_START:
            self.prompt.delete_to_start()
        elif action == KeyAction.DELETE_WORD:
            self.prompt.delete_word()
        elif action == KeyAction.LEFT:
            self.prompt.move_left()
        elif action == KeyAction.RIGHT:
            self.prompt.move_right()
        elif action == KeyAction.WORD_LEFT:
            self.prompt.move_word_left()
        elif action == KeyAction.WORD_RIGHT:
            self.prompt.move_word_right()
        elif action == KeyAction.START:
            self.prompt.move_start()
        elif action == KeyAction.END:
            self.prompt.move_end()
        elif action == KeyAction.UP:
            new_val = self.history.up(self.prompt.buffer)
            self.prompt.buffer = new_val
            self.prompt.cursor = len(new_val)
        elif action == KeyAction.DOWN:
            new_val = self.history.down(self.prompt.buffer)
            self.prompt.buffer = new_val
            self.prompt.cursor = len(new_val)
        elif action == KeyAction.ENTER:
            return True
        elif action == KeyAction.TAB:
            self.completer.start(self.prompt.buffer)
        elif action == KeyAction.MOUSE_SCROLL:
            # Handle mouse scroll - call on_scroll callback
            if self.on_scroll:
                if char == "up":
                    self.on_scroll(1)  # Scroll up = show older
                elif char == "down":
                    self.on_scroll(-1)  # Scroll down = show newer
            return False  # Don't consume the event, keep reading
        elif action in (KeyAction.SHIFT_TAB, KeyAction.ESC):
            pass

        self._refresh()
        return False

    def _apply_completion(self, completion: str) -> None:
        """Apply a completion to the current buffer."""
        text = self.prompt.buffer
        if completion.startswith("/"):
            self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
            return
        if "/" in completion:
            words = text.split()
            if words:
                self.prompt.buffer = " ".join(words[:-1]) + " " + completion + " "
                if len(words) == 1:
                    self.prompt.buffer = completion + " "
                self.prompt.cursor = len(self.prompt.buffer)
            else:
                self.prompt.buffer = completion + " "
                self.prompt.cursor = len(self.prompt.buffer)
            return
        words = text.split()
        if words:
            self.prompt.buffer = " ".join(words[:-1]) + " " + completion + " "
            if len(words) == 1:
                self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
        else:
            self.prompt.buffer = completion + " "
            self.prompt.cursor = len(self.prompt.buffer)
