"""CLI interface for Alfred using prompt_toolkit with patched stdout."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout as original_patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from src.agent import ToolEnd, ToolEvent, ToolStart
from src.alfred import Alfred
from src.interfaces.status import StatusData, StatusRenderer

PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "cursor": "ansigreen",
    }
)


@dataclass
class TextSegment:
    content: str


@dataclass
class ToolCallSegment:
    tool_name: str
    result: str
    is_error: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


Segment = TextSegment | ToolCallSegment


class ConversationBuffer:
    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self._current_text: str = ""
        self.panels_visible: bool = True

    def add_text(self, chunk: str) -> None:
        self._current_text += chunk

    def on_tool_start(self, tool_name: str) -> None:
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text))
            self._current_text = ""

    def on_tool_end(self, tool_name: str, result: str, is_error: bool) -> None:
        self.segments.append(
            ToolCallSegment(
                tool_name=tool_name,
                result=result,
                is_error=is_error,
            )
        )

    def toggle_panels(self) -> None:
        self.panels_visible = not self.panels_visible

    def clear(self) -> None:
        self.segments = []
        self._current_text = ""

    def render(self) -> list[RenderableType]:
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
        content = self._truncate_result(tool.result, tool.is_error)
        style = "red" if tool.is_error else "dim blue"
        return Panel(content, title=f"Tool: {tool.tool_name}", border_style=style, padding=(0, 1))

    @staticmethod
    def _truncate_result(result: str, is_error: bool) -> str:
        if is_error:
            return result
        lines = result.strip().split("\n")
        if len(lines) > 5:
            return "\n".join(lines[:5]) + f"\n[dim]... ({len(lines) - 5} more)[/dim]"
        if len(result) > 500:
            return result[:500] + "[dim]...[/dim]"
        return result


class CLIInterface:
    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console()
        self.buffer = ConversationBuffer()
        self.session: PromptSession[str] = PromptSession(message=">>> ", style=PROMPT_STYLE)
        self._is_streaming = False

    def _print_banner(self) -> None:
        banner = Panel(
            Text("Alfred - Your Persistent Memory Assistant", style="bold cyan", justify="center"),
            subtitle="exit to quit | compact for memory | Ctrl-T toggle tools",
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(banner)

    def _on_tool_event(self, event: ToolEvent) -> None:
        if isinstance(event, ToolStart):
            self.buffer.on_tool_start(event.tool_name)
        elif isinstance(event, ToolEnd):
            self.buffer.on_tool_end(event.tool_name, event.result, event.is_error)

    def _get_status_data(self) -> StatusData:
        return StatusData(
            model_name=self.alfred.model_name,
            usage=self.alfred.token_tracker.usage,
            context_tokens=self.alfred.token_tracker.context_tokens,
            memories_count=self.alfred.context_summary.memories_count,
            session_messages=self.alfred.context_summary.session_messages,
            prompt_sections=self.alfred.context_summary.prompt_sections,
            is_streaming=self._is_streaming,
        )

    def _bottom_toolbar(self) -> Any:
        """Return status as prompt_toolkit bottom toolbar."""
        status_data = self._get_status_data()
        renderer = StatusRenderer(status_data)
        return renderer.to_prompt_toolkit()

    @contextmanager
    def _patch_stdout_with_status(self) -> Iterator[None]:
        """Patch stdout for prompt_toolkit compatibility."""
        with original_patch_stdout():
            yield

    async def run(self) -> None:
        self._print_banner()

        kb = KeyBindings()

        @kb.add("c-t")
        def _toggle(event: object) -> None:
            self.buffer.toggle_panels()

        self.session = PromptSession(
            message=">>> ",
            style=PROMPT_STYLE,
            key_bindings=kb,
            bottom_toolbar=self._bottom_toolbar,
        )

        while True:
            try:
                with self._patch_stdout_with_status():
                    user_input = await self.session.prompt_async()
                user_input = user_input.strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]Goodbye![/]")
                break

            if not user_input:
                continue

            if user_input.lower() == "exit":
                self.console.print("[bold yellow]Goodbye![/]")
                break

            if user_input.lower() == "compact":
                result = await self.alfred.compact()
                self.console.print(f"[bold green]Alfred:[/bold green] {result}\n")
                continue

            self.buffer.clear()
            self._is_streaming = True

            try:
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
                        body = self.buffer.render()
                        live.update(Group(*body))

            except Exception as e:
                self.console.print(f"\n[bold red]Error: {e}[/]\n")
            finally:
                self._is_streaming = False
