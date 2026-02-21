"""CLI interface for Alfred using prompt_toolkit for async input."""

import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from src.agent import ToolEnd, ToolEvent, ToolStart
from src.alfred import Alfred
from src.interfaces.status import StatusData, StatusRenderer

# Styling for prompt_toolkit input
PROMPT_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "cursor": "ansigreen",
})

# ANSI escape codes for cursor/screen control
ANSI_CLEAR_SCREEN = "\033[2J"
ANSI_HOME = "\033[H"
ANSI_SAVE_CURSOR = "\033[s"
ANSI_RESTORE_CURSOR = "\033[u"
ANSI_HIDE_CURSOR = "\033[?25l"
ANSI_SHOW_CURSOR = "\033[?25h"


def ansi_move_to(row: int, col: int = 1) -> str:
    """Move cursor to specific row and column."""
    return f"\033[{row};{col}H"


def ansi_clear_line() -> str:
    """Clear current line."""
    return "\033[2K"


def ansi_clear_below() -> str:
    """Clear from cursor to end of screen."""
    return "\033[J"


@dataclass
class TextSegment:
    """A segment of markdown text."""
    content: str


@dataclass
class ToolCallSegment:
    """A tool call panel segment."""
    tool_name: str
    result: str
    is_error: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


Segment = TextSegment | ToolCallSegment


class ConversationBuffer:
    """Manages ordered conversation segments (text + tool panels)."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self._current_text: str = ""
        self.panels_visible: bool = True

    def add_text(self, chunk: str) -> None:
        """Add text chunk to current text buffer."""
        self._current_text += chunk

    def on_tool_start(self, tool_name: str) -> None:
        """Finalize current text buffer before tool executes."""
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text))
            self._current_text = ""

    def on_tool_end(self, tool_name: str, result: str, is_error: bool) -> None:
        """Add completed tool call as a segment."""
        self.segments.append(ToolCallSegment(
            tool_name=tool_name,
            result=result,
            is_error=is_error,
        ))

    def toggle_panels(self) -> None:
        """Toggle visibility of tool panels."""
        self.panels_visible = not self.panels_visible

    def clear(self) -> None:
        """Clear all segments."""
        self.segments = []
        self._current_text = ""

    def render(self) -> list[RenderableType]:
        """Render all segments as Rich renderables."""
        renderables: list[RenderableType] = []

        for segment in self.segments:
            if isinstance(segment, TextSegment) and segment.content:
                renderables.append(Markdown(segment.content))
            elif isinstance(segment, ToolCallSegment) and self.panels_visible:
                renderables.append(self._render_tool_panel(segment))

        if self._current_text:
            renderables.append(Markdown(self._current_text))

        return renderables

    def _render_tool_panel(self, tool: ToolCallSegment) -> Panel:
        """Render a tool call as a Rich Panel."""
        content = self._truncate_result(tool.result, tool.is_error)
        style = "red" if tool.is_error else "dim blue"
        return Panel(
            content,
            title=f"Tool: {tool.tool_name}",
            border_style=style,
            padding=(0, 1),
        )

    @staticmethod
    def _truncate_result(result: str, is_error: bool) -> str:
        """Smart truncation: show errors in full, truncate success."""
        if is_error:
            return result

        lines = result.strip().split("\n")
        if len(lines) > 5:
            return "\n".join(lines[:5]) + f"\n[dim]... ({len(lines) - 5} more lines)[/dim]"

        if len(result) > 500:
            return result[:500] + "[dim]...[/dim]"

        return result


class FixedLayout:
    """Manages fixed header layout with scrollable content."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.header_lines = 2  # Status line + separator
        self.footer_lines = 2  # Input area

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal dimensions (height, width)."""
        try:
            size = os.get_terminal_size()
            return size.lines, size.columns
        except OSError:
            # Fallback for non-terminal environments (tests, CI)
            return 24, 80

    def clear_screen(self) -> None:
        """Clear the screen."""
        if sys.stdout.isatty():
            sys.stdout.write(ANSI_CLEAR_SCREEN + ANSI_HOME)
            sys.stdout.flush()

    def render_header(self, header: RenderableType) -> None:
        """Render fixed header at top of screen."""
        if not sys.stdout.isatty():
            # No terminal - just print normally
            self.console.print(header)
            _, width = self.get_terminal_size()
            self.console.print("─" * width)
            return

        # Move to line 1
        sys.stdout.write(ansi_move_to(1))
        sys.stdout.write(ansi_clear_line())

        # Render header with Rich
        with self.console.capture() as capture:
            self.console.print(header, end="")
        header_text = capture.get()

        # Print each line, clearing as we go
        lines = header_text.split("\n")[:self.header_lines]
        for i, line in enumerate(lines):
            sys.stdout.write(ansi_move_to(i + 1) + ansi_clear_line() + line)

        # Add separator line
        _, width = self.get_terminal_size()
        sys.stdout.write(ansi_move_to(self.header_lines) + ansi_clear_line())
        sys.stdout.write("─" * width)
        sys.stdout.flush()

    def render_body(self, content: list[RenderableType]) -> None:
        """Render scrollable body content."""
        if not sys.stdout.isatty():
            # No terminal - just print content
            self.console.print(Group(*content))
            return

        height, width = self.get_terminal_size()

        # Body starts after header, ends before footer
        body_start = self.header_lines + 1
        body_height = height - self.header_lines - self.footer_lines
        body_height = max(body_height, 3)  # Minimum 3 lines for body

        # Render content to string
        with self.console.capture() as capture:
            self.console.print(Group(*content), end="")
        content_text = capture.get()
        content_lines = content_text.split("\n")

        # Calculate which lines to show (scroll to bottom)
        total_lines = len(content_lines)
        if total_lines <= body_height:
            visible_lines = content_lines
        else:
            # Show last body_height lines (scroll to bottom)
            visible_lines = content_lines[-body_height:]

        # Clear body region and render
        for i in range(body_height):
            row = body_start + i
            sys.stdout.write(ansi_move_to(row) + ansi_clear_line())
            if i < len(visible_lines):
                # Truncate line to terminal width
                line_text = visible_lines[i]
                line = line_text[:width] if len(line_text) > width else line_text
                sys.stdout.write(line)

        # Show scrollbar indicator if needed
        if total_lines > body_height:
            scroll_pct = 100  # Always at bottom
            self._render_scrollbar(body_start, body_height, scroll_pct)

        sys.stdout.flush()

    def _render_scrollbar(self, start_row: int, height: int, percent: int) -> None:
        """Render scrollbar on right edge."""
        _, width = self.get_terminal_size()
        col = width - 1

        thumb_pos = int((percent / 100) * (height - 1))

        for i in range(height):
            row = start_row + i
            sys.stdout.write(ansi_move_to(row, col))
            if i == thumb_pos:
                sys.stdout.write("▓")
            else:
                sys.stdout.write("░")

    def position_input(self) -> None:
        """Position cursor for input prompt."""
        if not sys.stdout.isatty():
            # No terminal - just show prompt
            self.console.print("[bold cyan]>>>[/] ", end="")
            return

        height, _ = self.get_terminal_size()
        input_row = height - self.footer_lines + 1

        # Clear input area
        for i in range(self.footer_lines):
            sys.stdout.write(ansi_move_to(height - self.footer_lines + 1 + i) + ansi_clear_line())

        # Position cursor and show prompt
        sys.stdout.write(ansi_move_to(input_row) + ansi_clear_line())
        sys.stdout.write("[bold cyan]>>>[/] ")
        sys.stdout.flush()

    def show_spinner(self, is_streaming: bool) -> None:
        """Show/hide spinner in header."""
        # This is handled by StatusRenderer
        pass


class CLIInterface:
    """CLI interface with fixed header and scrollable content."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console(force_terminal=True)
        self.buffer = ConversationBuffer()
        self.layout = FixedLayout(self.console)
        self.session: PromptSession[str] = PromptSession(
            message=">>> ",
            style=PROMPT_STYLE,
        )
        self._conversation_history: list[RenderableType] = []

    def _print_banner(self) -> None:
        """Print banner once at startup."""
        banner = Panel(
            Text(
                "🎩 Alfred - Your Persistent Memory Assistant",
                style="bold cyan",
                justify="center",
            ),
            subtitle="exit to quit • compact for memory • Ctrl-T toggle tools",
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(banner)
        # Only wait for input if we have a real terminal
        if sys.stdin.isatty():
            self.console.print("[dim]Press Enter to continue...[/]")
            input()

    def _on_tool_event(self, event: ToolEvent) -> None:
        """Callback for tool execution events from agent."""
        if isinstance(event, ToolStart):
            self.buffer.on_tool_start(event.tool_name)
        elif isinstance(event, ToolEnd):
            self.buffer.on_tool_end(
                tool_name=event.tool_name,
                result=event.result,
                is_error=event.is_error,
            )

    def _render_header(self, is_streaming: bool = False) -> RenderableType:
        """Render the status header."""
        status_data = StatusData(
            model_name=self.alfred.model_name,
            usage=self.alfred.token_tracker.usage,
            context_tokens=self.alfred.token_tracker.context_tokens,
            is_streaming=is_streaming,
        )
        return StatusRenderer(status_data).render()

    def _refresh_screen(self, is_streaming: bool = False) -> None:
        """Refresh the entire screen with header and content."""
        self.layout.render_header(self._render_header(is_streaming))

        # Combine history + current buffer
        all_content = self._conversation_history + self.buffer.render()
        self.layout.render_body(all_content)

    async def run(self) -> None:
        """Run interactive CLI with fixed header."""
        self._print_banner()
        self.layout.clear_screen()

        # Set up keybindings
        kb = KeyBindings()

        @kb.add("c-t")
        def _toggle_tool_panels(event: object) -> None:
            """Toggle tool panels on Ctrl-T."""
            self.buffer.toggle_panels()
            self._refresh_screen()

        self.session = PromptSession(
            message=">>> ",
            style=PROMPT_STYLE,
            key_bindings=kb,
        )

        while True:
            # Refresh screen before getting input
            self._refresh_screen(is_streaming=False)
            self.layout.position_input()

            try:
                # Get input
                with patch_stdout():
                    user_input = await self.session.prompt_async()
                user_input = user_input.strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]Goodbye! 👋[/bold yellow]")
                break

            if not user_input:
                continue

            if user_input.lower() == "exit":
                self.layout.clear_screen()
                self.console.print("[bold yellow]Goodbye! 👋[/bold yellow]")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                self._conversation_history.append(
                    Text(f"[bold green]Alfred:[/] {result}", style="default")
                )
                continue

            # Add user message to history
            self._conversation_history.append(
                Text(f"[bold cyan]You:[/] {user_input}", style="default")
            )

            # Clear buffer for new response
            self.buffer.clear()

            # Stream response
            try:
                async for chunk in self.alfred.chat_stream(
                    user_input,
                    tool_callback=self._on_tool_event,
                ):
                    self.buffer.add_text(chunk)
                    self._refresh_screen(is_streaming=True)
                    self.layout.position_input()

                # Add response to history
                for item in self.buffer.render():
                    self._conversation_history.append(item)

                # Clear buffer for next turn
                self.buffer.clear()

            except Exception as e:
                self._conversation_history.append(
                    Text(f"[bold red]Error:[/] {e}", style="default")
                )

        # Cleanup
        self.layout.clear_screen()
