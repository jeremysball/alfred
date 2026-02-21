"""CLI interface for Alfred using prompt_toolkit for async input."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group, RenderableType
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


class CLIInterface:
    """CLI interface with async prompt and streaming output capture."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console()
        self.buffer = ConversationBuffer()
        self.session: PromptSession[str] = PromptSession(
            message=[("class:prompt", "You: ")],
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
            subtitle="Type 'exit' to quit • 'compact' to compact memory • Ctrl-T to toggle tools",
            border_style="cyan",
            padding=(1, 2),
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

    async def run(self) -> None:
        """Run interactive CLI with async input and streaming output."""
        self._print_banner()

        # Set up keybindings for Ctrl-t
        kb = KeyBindings()

        @kb.add("c-t")
        def _toggle_tool_panels(event: object) -> None:
            """Toggle tool panels on Ctrl-T."""
            self.buffer.toggle_panels()

        # Update session with keybindings
        self.session = PromptSession(
            message=[("class:prompt", "You: ")],
            style=PROMPT_STYLE,
            key_bindings=kb,
        )

        while True:
            try:
                # Use patch_stdout to allow streaming output during prompt
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

            # Stream response with Rich Live for proper markdown rendering + status
            self.console.print("[bold magenta]Alfred:[/bold magenta]")

            try:
                # Create status data and renderer
                status_data = StatusData(
                    model_name=self.alfred.model_name,
                    usage=self.alfred.token_tracker.usage,
                    context_tokens=self.alfred.token_tracker.context_tokens,
                    is_streaming=True,
                )
                status_renderer = StatusRenderer(status_data)

                with Live(
                    console=self.console,
                    refresh_per_second=10,
                    vertical_overflow="visible",
                ) as live:
                    async for chunk in self.alfred.chat_stream(
                        user_input,
                        tool_callback=self._on_tool_event,
                    ):
                        self.buffer.add_text(chunk)
                        # Update usage reference for latest counts
                        status_data.usage = self.alfred.token_tracker.usage
                        status_data.context_tokens = self.alfred.token_tracker.context_tokens

                        # Render segments + status line
                        segments = self.buffer.render()
                        status_text = status_renderer.render()
                        live.update(Group(*segments, Text(), status_text))

                    # Final update with idle state
                    status_data.is_streaming = False
                    segments = self.buffer.render()
                    status_text = status_renderer.render()
                    live.update(Group(*segments, Text(), status_text))

                self.console.print()  # Final newline
            except Exception as e:
                self.console.print(f"\n[bold red][Error: {e}][/bold red]\n")
