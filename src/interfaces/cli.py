"""CLI interface for Alfred using prompt_toolkit for async input."""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
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


# Type for conversation segments
Segment = TextSegment | ToolCallSegment


class ConversationBuffer:
    """Manages ordered conversation segments (text + tool panels)."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self._current_text: str = ""
        self._pending_tool: ToolCallSegment | None = None
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
        self._pending_tool = None

    def render(self) -> list[RenderableType]:
        """Render all segments as Rich renderables."""
        renderables: list[RenderableType] = []

        # Render completed segments
        for segment in self.segments:
            if isinstance(segment, TextSegment) and segment.content:
                renderables.append(Markdown(segment.content))
            elif isinstance(segment, ToolCallSegment) and self.panels_visible:
                renderables.append(self._render_tool_panel(segment))

        # Render current text buffer (not yet finalized)
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


class LayoutManager:
    """Manages fixed layout with header, scrollable body, and input footer."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self._scroll_offset: int = 0
        self._total_lines: int = 0

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal dimensions (height, width)."""
        try:
            size = os.get_terminal_size()
            return size.lines, size.columns
        except OSError:
            return 24, 80  # Fallback

    def render_frame(
        self,
        header: RenderableType,
        body: list[RenderableType],
    ) -> Layout:
        """Create layout with header, body, and scrollbar."""
        height, width = self.get_terminal_size()

        # Reserve lines: 2 for header, 3 for input area, 1 for scrollbar
        body_height = max(height - 5, 5)

        layout = Layout()
        layout.split_column(
            Layout(header, name="header", size=2),
            Layout(name="body", size=body_height),
            Layout(name="input", size=3),
        )

        # Add scrollbar to body
        body_content = self._add_scrollbar(body, body_height, width)
        layout["body"].update(body_content)
        layout["header"].update(header)

        return layout

    def _add_scrollbar(
        self,
        body: list[RenderableType],
        body_height: int,
        width: int,
    ) -> RenderableType:
        """Add scrollbar indicator to body content."""
        # Estimate total lines from body content
        # (This is approximate - actual rendering may differ)
        total_segments = len(body)
        estimated_lines = total_segments * 3  # Rough estimate

        if estimated_lines <= body_height:
            # No scrollbar needed
            return Group(*body)

        # Calculate scroll position
        if self._scroll_offset + body_height >= estimated_lines:
            # At bottom
            scroll_percent = 100
        else:
            max_scroll = max(estimated_lines - body_height, 1)
            scroll_percent = int((self._scroll_offset / max_scroll) * 100)

        # Create scrollbar indicator
        scrollbar = self._create_scrollbar(scroll_percent, body_height)

        # Create layout with content and scrollbar
        inner = Layout()
        inner.split_row(
            Layout(Group(*body), name="content", ratio=1),
            Layout(scrollbar, name="scrollbar", size=1),
        )
        return inner

    def _create_scrollbar(self, percent: int, height: int) -> Text:
        """Create a vertical scrollbar indicator."""
        # Use block characters for scrollbar
        # █ = full, ░ = empty, ▓ = thumb
        thumb_pos = int((percent / 100) * (height - 1))

        lines = []
        for i in range(height):
            if i == thumb_pos:
                lines.append("▓")
            elif i < thumb_pos:
                lines.append("░")
            else:
                lines.append("░")

        return Text("\n".join(lines), style="dim")

    def scroll_to_bottom(self) -> None:
        """Reset scroll to bottom (newest content)."""
        self._scroll_offset = 0

    def position_cursor_for_input(self) -> None:
        """Move cursor to input area at bottom of screen."""
        height, _ = self.get_terminal_size()
        # Move cursor to input line (height - 2)
        self.console.print(f"\033[{height - 2};1H", end="")

    def clear_input_area(self) -> None:
        """Clear the input area."""
        height, width = self.get_terminal_size()
        # Clear the input lines
        self.console.print(f"\033[{height - 2};1H\033[2K", end="")
        self.console.print(f"\033[{height - 1};1H\033[2K", end="")

    def render_input_prompt(self) -> None:
        """Render the input prompt at bottom."""
        height, _ = self.get_terminal_size()
        # Move to input line and show prompt
        self.console.print(f"\033[{height - 2};1H", end="")
        self.console.print("[bold cyan]>>>[/] ", end="")


class CLIInterface:
    """CLI interface with async prompt and streaming output capture."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console()
        self.buffer = ConversationBuffer()
        self.layout = LayoutManager(self.console)
        self.session: PromptSession[str] = PromptSession(
            message=">>> ",
            style=PROMPT_STYLE,
        )

    def _print_banner(self) -> None:
        """Print a welcoming banner."""
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
        self.console.print()

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

    async def run(self) -> None:
        """Run interactive CLI with fixed layout and streaming output."""
        self._print_banner()

        # Set up keybindings
        kb = KeyBindings()

        @kb.add("c-t")
        def _toggle_tool_panels(event: object) -> None:
            """Toggle tool panels on Ctrl-T."""
            self.buffer.toggle_panels()

        # Update session with keybindings and new prompt
        self.session = PromptSession(
            message=">>> ",
            style=PROMPT_STYLE,
            key_bindings=kb,
        )

        while True:
            try:
                # Get input (prompt_toolkit handles display)
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
                self.console.print("[bold yellow]Goodbye! 👋[/bold yellow]")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                self.console.print(f"[bold green]Alfred:[/bold green] {result}\n")
                continue

            # Clear previous conversation for this turn
            self.buffer.clear()

            # Stream response with fixed layout
            try:
                with Live(
                    console=self.console,
                    refresh_per_second=10,
                    vertical_overflow="visible",
                ) as live:
                    # Initial frame with streaming header
                    live.update(Group(
                        self._render_header(is_streaming=True),
                        Text(),
                        Text("[dim]Waiting for response...[/]"),
                    ))

                    async for chunk in self.alfred.chat_stream(
                        user_input,
                        tool_callback=self._on_tool_event,
                    ):
                        self.buffer.add_text(chunk)

                        # Render with header + body + scrollbar
                        body = self.buffer.render()
                        layout = self.layout.render_frame(
                            header=self._render_header(is_streaming=True),
                            body=body,
                        )
                        live.update(layout)

                    # Final update with idle state
                    body = self.buffer.render()
                    layout = self.layout.render_frame(
                        header=self._render_header(is_streaming=False),
                        body=body,
                    )
                    live.update(layout)

                self.console.print()  # Final newline
            except Exception as e:
                self.console.print(f"\n[bold red][Error: {e}][/bold red]\n")
