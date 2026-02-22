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
from rich.table import Table
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

    # === Session Commands ===

    def _handle_session_command(self, input: str) -> bool:
        """Handle session commands. Returns True if handled."""
        parts = input.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if cmd == "/new":
            return self._cmd_new_session()
        elif cmd == "/resume":
            return self._cmd_resume_session(arg)
        elif cmd == "/sessions":
            return self._cmd_list_sessions()
        elif cmd == "/session":
            return self._cmd_show_current_session()
        return False

    def _cmd_new_session(self) -> bool:
        """Create a new session."""
        session = self.alfred.session_manager.new_session()
        self.buffer.clear()
        self.console.print(
            Panel(
                f"Session ID: [bold cyan]{session.meta.session_id}[/]",
                title="New Session Created",
                border_style="green",
            )
        )
        return True

    def _cmd_resume_session(self, session_id: str | None) -> bool:
        """Resume an existing session."""
        if not session_id:
            self.console.print(
                "[bold red]Usage: /resume <session_id>[/]\n"
                "Use [bold]/sessions[/] to see available sessions.\n"
            )
            return True

        try:
            session = self.alfred.session_manager.resume_session(session_id)
            self.buffer.clear()
            msg_count = len(session.messages)
            self.console.print(
                Panel(
                    f"Session ID: [bold cyan]{session_id}[/]\n"
                    f"Messages: {msg_count}",
                    title="Session Resumed",
                    border_style="green",
                )
            )
        except ValueError as e:
            self.console.print(f"[bold red]Error: {e}[/]\n")
        return True

    def _cmd_list_sessions(self) -> bool:
        """List all sessions."""
        sessions = self.alfred.session_manager.list_sessions()

        if not sessions:
            self.console.print("[bold yellow]No sessions found.[/]\n")
            return True

        table = Table(title="Sessions", border_style="dim blue")
        table.add_column("ID", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Last Active", style="dim")
        table.add_column("Messages", justify="right")

        current_id = None
        if self.alfred.session_manager.has_active_session():
            current = self.alfred.session_manager.get_current_cli_session()
            if current:
                current_id = current.meta.session_id

        for meta in sessions:
            # Format timestamps
            created = meta.created_at.strftime("%Y-%m-%d %H:%M")
            last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

            # Mark current session
            id_str = meta.session_id
            if meta.session_id == current_id:
                id_str = f"[bold]{meta.session_id}[/] *"

            table.add_row(id_str, created, last_active, str(meta.message_count))

        self.console.print(table)
        self.console.print()
        return True

    def _cmd_show_current_session(self) -> bool:
        """Show current session details."""
        if not self.alfred.session_manager.has_active_session():
            self.console.print("[bold yellow]No active session.[/]\n")
            return True

        session = self.alfred.session_manager.get_current_cli_session()
        if not session:
            self.console.print("[bold yellow]No active session.[/]\n")
            return True

        meta = session.meta
        created = meta.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

        self.console.print(
            Panel(
                f"ID: [bold cyan]{meta.session_id}[/]\n"
                f"Status: {meta.status}\n"
                f"Created: {created}\n"
                f"Last Active: {last_active}\n"
                f"Messages: {meta.message_count}",
                title="Current Session",
                border_style="cyan",
            )
        )
        return True

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

            # Session commands
            if user_input.startswith("/") and self._handle_session_command(user_input):
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
