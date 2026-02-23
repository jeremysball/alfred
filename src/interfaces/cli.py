"""CLI interface for Alfred using Rich Live with custom prompt."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from src.agent import ToolEnd, ToolEvent, ToolStart
from src.alfred import Alfred
from src.cron.notifier import CLINotifier
from src.interfaces.live_display import LiveDisplay
from src.interfaces.notification_buffer import NotificationBuffer
from src.interfaces.status import StatusData
from src.session import Session


@dataclass
class TextSegment:
    content: str
    role: str = "assistant"  # "user" or "assistant"


@dataclass
class ToolCallSegment:
    tool_name: str
    result: str
    is_error: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


Segment = TextSegment | ToolCallSegment


class ConversationBuffer:
    """Buffer for accumulating conversation content (messages and tool calls)."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self._current_text: str = ""
        self._current_role: str = "assistant"
        self.panels_visible: bool = True

    def add_user_message(self, content: str) -> None:
        """Add a complete user message as a segment."""
        # Flush any pending assistant text first
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text, role=self._current_role))
            self._current_text = ""
        self.segments.append(TextSegment(content=content, role="user"))

    def add_system_message(self, title: str, content: str, border_style: str = "green") -> None:
        """Add a system/command message as a styled panel."""
        # Flush any pending text first
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text, role=self._current_role))
            self._current_text = ""
        # Create a TextSegment that will render as a system panel
        segment = TextSegment(content=f"__SYSTEM__:{title}:{border_style}:{content}", role="system")
        self.segments.append(segment)

    def add_text(self, chunk: str, role: str = "assistant") -> None:
        """Add text chunk to current message."""
        self._current_text += chunk
        self._current_role = role

    def finalize_message(self) -> None:
        """Finalize current message and add to segments."""
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text, role=self._current_role))
            self._current_text = ""
            self._current_role = "assistant"

    def on_tool_start(self, tool_name: str) -> None:
        """Called when a tool starts - flush current text to segments."""
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text, role=self._current_role))
            self._current_text = ""

    def on_tool_end(self, tool_name: str, result: str, is_error: bool) -> None:
        """Called when a tool ends - add tool segment."""
        self.segments.append(
            ToolCallSegment(
                tool_name=tool_name,
                result=result,
                is_error=is_error,
            )
        )

    def toggle_panels(self) -> None:
        """Toggle visibility of tool panels."""
        self.panels_visible = not self.panels_visible

    def clear(self) -> None:
        """Clear all content."""
        self.segments = []
        self._current_text = ""
        self._current_role = "assistant"

    def render(self) -> list[RenderableType]:
        """Render all segments as Rich renderables."""
        renderables: list[RenderableType] = []

        for segment in self.segments:
            if isinstance(segment, TextSegment) and segment.content:
                renderables.append(self._render_message_panel(segment))
            elif isinstance(segment, ToolCallSegment) and self.panels_visible:
                renderables.append(self._render_tool_panel(segment))

        if self._current_text:
            segment = TextSegment(content=self._current_text, role=self._current_role)
            renderables.append(self._render_message_panel(segment))

        return renderables

    def _render_message_panel(self, segment: TextSegment) -> Panel:
        """Render a message as a styled Panel."""
        # Handle system messages specially
        if segment.role == "system" and segment.content.startswith("__SYSTEM__:"):
            parts = segment.content.split(":", 3)
            if len(parts) == 4:
                title = parts[1]
                border_style = parts[2]
                content = parts[3]
                return Panel(
                    content,
                    title=title,
                    title_align="left",
                    border_style=border_style,
                    padding=(0, 1),
                )
        title = "You" if segment.role == "user" else "Alfred"
        style = "color(23)" if segment.role == "user" else "color(24)"  # Slate blue / Dark teal
        return Panel(
            Markdown(segment.content),
            title=title,
            title_align="left",
            border_style=style,
            padding=(0, 1),
        )

    def _render_tool_panel(self, tool: ToolCallSegment) -> Panel:
        """Render a tool call as a styled Panel."""
        content = self._truncate_result(tool.result, tool.is_error)
        style = "red" if tool.is_error else "dim blue"
        return Panel(
            content,
            title=f"Tool: {tool.tool_name}",
            title_align="left",
            border_style=style,
            padding=(0, 1),
        )

    @staticmethod
    def _truncate_result(result: str, is_error: bool) -> str:
        """Truncate long tool results."""
        if is_error:
            return result
        lines = result.strip().split("\n")
        if len(lines) > 5:
            return "\n".join(lines[:5]) + f"\n[dim]... ({len(lines) - 5} more)[/dim]"
        if len(result) > 500:
            return result[:500] + "[dim]...[/dim]"
        return result


class CLIInterface:
    """CLI interface using Rich Live with custom prompt input."""

    def __init__(self, alfred: Alfred) -> None:
        self.alfred = alfred
        self.console = Console()
        self.buffer = ConversationBuffer()
        self._is_streaming = False
        self._live_display: LiveDisplay | None = None

        # Set up notification buffer for CLI mode
        self._notification_buffer = NotificationBuffer(
            is_active_callback=lambda: self._is_streaming
        )

        # Wire buffer to notifier if using CLINotifier
        self._cli_notifier: CLINotifier | None = None
        if isinstance(alfred.notifier, CLINotifier):
            alfred.notifier.set_buffer(self._notification_buffer)
            alfred.notifier.set_console(self.console)
            self._cli_notifier = alfred.notifier

    def _print_banner(self) -> None:
        """Print the welcome banner."""
        banner = Panel(
            Text("Alfred - Your Persistent Memory Assistant", style="bold cyan", justify="center"),
            subtitle="exit to quit | compact for memory | Ctrl-T toggle tools",
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(banner)

    def _display_session_history(self, session: Session) -> None:
        """Display conversation history from a session in the terminal."""
        if not session.messages:
            return

        self.console.print()

        for msg in session.messages:
            if msg.role.value == "user":
                panel = Panel(
                    msg.content,
                    title="You",
                    title_align="left",
                    border_style="color(23)",  # Dark slate blue
                    padding=(0, 1),
                )
                self.console.print(panel)
            elif msg.role.value == "assistant":
                panel = Panel(
                    Markdown(msg.content),
                    title="Alfred",
                    title_align="left",
                    border_style="color(24)",  # Dark teal
                    padding=(0, 1),
                )
                self.console.print(panel)
            elif msg.role.value == "system":
                self.console.print(f"[dim italic][System: {msg.content}][/]")

        self.console.print()

    def _on_tool_event(self, event: ToolEvent) -> None:
        """Handle tool events from the agent."""
        if isinstance(event, ToolStart):
            self.buffer.on_tool_start(event.tool_name)
        elif isinstance(event, ToolEnd):
            self.buffer.on_tool_end(event.tool_name, event.result, event.is_error)

    def _get_status_data(self) -> StatusData:
        """Get current status data for status line."""
        return StatusData(
            model_name=self.alfred.model_name,
            usage=self.alfred.token_tracker.usage,
            context_tokens=self.alfred.token_tracker.context_tokens,
            memories_count=self.alfred.context_summary.memories_count,
            session_messages=self.alfred.context_summary.session_messages,
            prompt_sections=self.alfred.context_summary.prompt_sections,
            is_streaming=self._is_streaming,
        )

    def _get_history_path(self) -> str | None:
        """Get path to session history file."""
        if self.alfred.session_manager.has_active_session():
            session = self.alfred.session_manager.get_current_cli_session()
            if session:
                from pathlib import Path

                session_dir = Path("data/sessions") / session.meta.session_id
                return str(session_dir / "history.txt")
        return None

    # === Session Commands ===

    def _handle_session_command(self, user_input: str) -> bool:
        """Handle session commands. Returns True if handled."""
        parts = user_input.split(maxsplit=1)
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

        # Clear LiveDisplay content to remove old messages
        if self._live_display:
            self._live_display.clear_content()

        # Reset token tracking for new session
        self.alfred.token_tracker.reset()

        # Update context summary for status line
        self.alfred.context_summary.update(
            memories_count=self.alfred.context_summary.memories_count,
            session_messages=0,
        )

        # Update status line immediately
        if self._live_display:
            self._live_display.set_status(self._render_status_line())
            self._live_display.update()

        # Add system message to buffer (appears inline in conversation)
        self.buffer.add_system_message(
            "New Session Created",
            f"Session ID: [bold cyan]{session.meta.session_id}[/]",
            "green",
        )
        return True

    def _cmd_resume_session(self, session_id: str | None) -> bool:
        """Resume an existing session."""
        if not session_id:
            self.buffer.add_system_message(
                "Usage",
                "[bold red]/resume <session_id>[/]\n"
                "Use [bold]/sessions[/] to see available sessions.",
                "red",
            )
            return True

        try:
            session = self.alfred.session_manager.resume_session(session_id)
            self.buffer.clear()
            msg_count = len(session.messages)

            # Clear LiveDisplay content to remove old messages
            if self._live_display:
                self._live_display.clear_content()

            # Update context summary for status line
            self.alfred.context_summary.update(
                memories_count=self.alfred.context_summary.memories_count,
                session_messages=msg_count,
            )

            # Update status line immediately
            if self._live_display:
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()

            self.buffer.add_system_message(
                "Session Resumed",
                f"Session ID: [bold cyan]{session_id}[/]\nMessages: {msg_count}",
                "green",
            )

            # Display conversation history
            if session.messages:
                self._display_session_history(session)

        except ValueError as e:
            self.buffer.add_system_message(
                "Error",
                f"[bold red]{e}[/]",
                "red",
            )
        return True

    def _cmd_list_sessions(self) -> bool:
        """List all sessions."""
        sessions = self.alfred.session_manager.list_sessions()

        if not sessions:
            self.buffer.add_system_message(
                "Sessions",
                "[bold yellow]No sessions found.[/]",
                "yellow",
            )
            return True

        # Build a text representation of the sessions table
        lines = ["[bold]Sessions[/bold]", ""]
        lines.append("[cyan]ID[/cyan] | [dim]Created[/dim] | [dim]Last Active[/dim] | Messages")
        lines.append("-" * 60)

        current_id = None
        if self.alfred.session_manager.has_active_session():
            current = self.alfred.session_manager.get_current_cli_session()
            if current:
                current_id = current.meta.session_id

        for meta in sessions:
            created = meta.created_at.strftime("%Y-%m-%d %H:%M")
            last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")
            if meta.session_id == current_id:
                id_str = f"[bold]{meta.session_id}[/bold] *"
            else:
                id_str = meta.session_id
            lines.append(f"{id_str} | {created} | {last_active} | {meta.message_count}")

        self.buffer.add_system_message(
            "Sessions",
            "\n".join(lines),
            "dim blue",
        )
        return True

    def _cmd_show_current_session(self) -> bool:
        """Show current session details."""
        if not self.alfred.session_manager.has_active_session():
            self.buffer.add_system_message(
                "Current Session",
                "[bold yellow]No active session.[/]",
                "yellow",
            )
            return True

        session = self.alfred.session_manager.get_current_cli_session()
        if not session:
            self.buffer.add_system_message(
                "Current Session",
                "[bold yellow]No active session.[/]",
                "yellow",
            )
            return True

        meta = session.meta
        created = meta.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

        content = (
            f"ID: [bold cyan]{meta.session_id}[/]\n"
            f"Status: {meta.status}\n"
            f"Created: {created}\n"
            f"Last Active: {last_active}\n"
            f"Messages: {meta.message_count}"
        )
        self.buffer.add_system_message(
            "Current Session",
            content,
            "cyan",
        )
        return True

    async def run(self) -> None:
        """Main CLI loop."""
        self._print_banner()

        # Display session history if resuming an existing session
        if self.alfred.session_manager.has_active_session():
            session = self.alfred.session_manager.get_current_cli_session()
            if session:
                # Update context summary with session message count for status line
                msg_count = len(session.messages)
                self.alfred.context_summary.update(
                    memories_count=self.alfred.context_summary.memories_count,
                    session_messages=msg_count,
                )
                if session.messages:
                    self._display_session_history(session)

        # Create callback for session ID completion
        def get_session_ids() -> list[str]:
            return [meta.session_id for meta in self.alfred.session_manager.list_sessions()]

        # Create LiveDisplay
        self._live_display = LiveDisplay(
            console=self.console,
            history_path=self._get_history_path(),
            get_session_ids=get_session_ids,
        )

        with self._live_display:
            # Set initial status before first prompt
            self._live_display.set_status(self._render_status_line())

            while True:
                # Update status line (idle state)
                self._live_display.set_status(self._render_status_line())

                try:
                    user_input = await self._live_display.read_line_async()
                    user_input = user_input.strip()
                except EOFError:
                    break
                except KeyboardInterrupt:
                    self.console.print("\n[bold yellow]Goodbye![/]")
                    break

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() == "exit":
                    # Exit Live display cleanly before breaking
                    if self._live_display:
                        self._live_display.stop()
                    self.console.print("[bold yellow]Goodbye![/]")
                    break

                if user_input.lower() == "compact":
                    result = await self.alfred.compact()
                    self.buffer.add_system_message(
                        "Memory Compacted",
                        f"[bold green]{result}[/]",
                        "green",
                    )
                    continue

                # Handle Ctrl+T toggle (as command for now)
                if user_input.lower() == "/toggle":
                    self.buffer.toggle_panels()
                    state = "visible" if self.buffer.panels_visible else "hidden"
                    self.buffer.add_system_message(
                        "Tool Panels",
                        f"Tool panels: {state}",
                        "dim",
                    )
                    continue

                # Session commands
                if user_input.startswith("/") and self._handle_session_command(user_input):
                    continue

                # Stream response
                await self._stream_response(user_input)

    async def _stream_response(self, user_input: str) -> None:
        """Stream a response from Alfred."""
        # Don't clear buffer - accumulate conversation history
        self._is_streaming = True

        # Add user message to buffer before streaming response
        self.buffer.add_user_message(user_input)

        # Disable echo during streaming to prevent Enter keystrokes from appearing
        if self._live_display:
            self._live_display.disable_echo()

        try:
            # Update display immediately to show throbber
            if self._live_display:
                self._live_display.set_content(self.buffer.render())
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()

            async for chunk in self.alfred.chat_stream(
                user_input,
                tool_callback=self._on_tool_event,
            ):
                self.buffer.add_text(chunk)

                # Update LiveDisplay content and status
                if self._live_display:
                    self._live_display.set_content(self.buffer.render())
                    self._live_display.set_status(self._render_status_line())
                    self._live_display.update()

            # Finalize the assistant message
            self.buffer.finalize_message()

            # Final update
            if self._live_display:
                self._live_display.set_content(self.buffer.render())
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()

        except Exception as e:
            self.console.print(f"\n[bold red]Error: {e}[/]\n")
        finally:
            self._is_streaming = False
            self._flush_notifications()
            # Re-enable echo after streaming
            if self._live_display:
                self._live_display.enable_echo()

    def _render_status_line(self) -> RenderableType:
        """Render status line at bottom.

        Shows: ⠋ kimi | in:12K out:3K | ctx:45%  📚 0 | 💬 0
        When streaming: animated spinner
        When idle: static ">"
        """
        status_data = self._get_status_data()
        usage = status_data.usage

        # Build status text - no background, clean style
        text = Text()

        # Model name
        text.append(status_data.model_name, style="bold cyan")
        text.append(" | ", style="dim")

        # Token counts
        text.append(f"in:{self._format_number(usage.input_tokens)} ", style="cyan")
        text.append(f"out:{self._format_number(usage.output_tokens)}", style="green")
        if usage.cache_read_tokens > 0:
            cache = self._format_number(usage.cache_read_tokens)
            text.append(f" cache:{cache}", style="yellow")
        if usage.reasoning_tokens > 0:
            reason = self._format_number(usage.reasoning_tokens)
            text.append(f" reason:{reason}", style="magenta")

        # Context percentage
        text.append(f" | ctx:{self._format_number(status_data.context_tokens)}", style="dim")

        # Memory and message counts
        m = status_data.memories_count
        s = status_data.session_messages
        text.append(f"  📚 {m} | 💬 {s}", style="white")

        # Throbber: animated spinner when streaming, static ">" when idle
        if self._is_streaming:
            from rich.columns import Columns
            spinner = Spinner("dots", style="cyan")
            return Columns([spinner, text])
        else:
            prefix = Text("> ", style="green")
            prefix.append(text)
            return prefix

    @staticmethod
    def _format_number(n: int) -> str:
        """Format number with K suffix for thousands."""
        if n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(n)

    def _flush_notifications(self) -> None:
        """Flush queued notifications from buffer."""
        if self._cli_notifier and self._notification_buffer.has_pending():
            self._cli_notifier.flush_buffer()
