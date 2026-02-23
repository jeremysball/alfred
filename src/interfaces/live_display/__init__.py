"""Rich Live display with custom prompt input."""

import asyncio
import contextlib
import signal
import sys
import termios
import threading
from collections.abc import Callable

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text

from .completer import Completer
from .history import History
from .input import InputReader, KeyAction, PromptInput


class LiveDisplay:
    """Rich Live display with streaming content and custom prompt."""

    def __init__(
        self,
        console: Console | None = None,
        history_path: str | None = None,
        get_session_ids: Callable[[], list[str]] | None = None,
    ) -> None:
        """Initialize LiveDisplay."""
        self.console = console or Console()
        self.prompt = PromptInput()
        self.history = History(history_path)
        self.reader = InputReader()
        self.completer = Completer(get_session_ids=get_session_ids)
        self._live: Live | None = None
        self._content: list[RenderableType] = []
        self._status: RenderableType = Text("Ready", style="dim")
        self._heartbeat_thread: threading.Thread | None = None
        self._stop_heartbeat = threading.Event()

    def set_content(self, renderables: list[RenderableType]) -> None:
        """Set content area to list of renderables."""
        self._content = renderables
        self._refresh()

    def add_content(self, renderable: RenderableType) -> None:
        """Add a renderable to content area."""
        self._content.append(renderable)
        self._refresh()

    def clear_content(self) -> None:
        """Clear content area (new message)."""
        self._content = []
        self._refresh()

    def set_status(self, status: RenderableType) -> None:
        """Update status line."""
        self._status = status
        self._refresh()

    def _render(self) -> RenderableType:
        """Render full display: content + dropdown + prompt + status."""
        parts: list[RenderableType] = []
        if self._content:
            parts.extend(self._content)
        if self.completer.visible:
            parts.append(self.completer.render_dropdown())
        parts.append(self.prompt.render())
        parts.append(self._status)
        return Group(*parts)

    def _refresh(self) -> None:
        """Refresh Live display if active."""
        if self._live is not None:
            self._live.update(self._render())

    def start(self) -> None:
        """Start Live display."""
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=10,
            vertical_overflow="visible",
        )
        self._live.start()
        # Handle terminal resize to force redraw
        self._setup_resize_handler()
        # Start heartbeat to keep display alive during tmux window switches
        self._start_heartbeat()

    def _setup_resize_handler(self) -> None:
        """Setup handler for terminal resize events."""
        if sys.stdin.isatty():
            # Save original handler
            self._original_sigwinch = signal.signal(signal.SIGWINCH, self._on_resize)

    def _on_resize(self, signum: int, frame: object) -> None:
        """Handle terminal resize - force a refresh."""
        # Force a refresh on resize
        self._refresh()

    def _start_heartbeat(self) -> None:
        """Start background heartbeat thread to keep display alive."""
        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        """Background loop that periodically refreshes the display.

        This keeps the terminal connection alive when switching tmux windows
        or when the terminal loses focus.
        """
        while not self._stop_heartbeat.is_set():
            # Refresh every 2 seconds to keep display alive
            self._stop_heartbeat.wait(2.0)
            if not self._stop_heartbeat.is_set() and self._live is not None:
                with contextlib.suppress(Exception):
                    self._refresh()

    def _stop_heartbeat_thread(self) -> None:
        """Stop the heartbeat thread."""
        self._stop_heartbeat.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=0.5)

    def stop(self) -> None:
        """Stop Live display."""
        # Stop heartbeat first
        self._stop_heartbeat_thread()
        if self._live is not None:
            self._live.stop()
            self._live = None
        # Restore original resize handler
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
        """Disable terminal echo - prevents keystrokes from appearing during streaming."""
        if not sys.stdin.isatty():
            return
        fd = sys.stdin.fileno()
        self._original_tty_settings = termios.tcgetattr(fd)
        new_settings = termios.tcgetattr(fd)
        new_settings[3] = new_settings[3] & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, new_settings)

    def enable_echo(self) -> None:
        """Re-enable terminal echo after streaming."""
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
            # Auto-trigger completion only for commands (starting with /)
            # Only when / is the FIRST character and followed by at least one letter
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
