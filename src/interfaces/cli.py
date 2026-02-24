"""CLI interface for Alfred using Rich Live with custom prompt."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from src.agent import ToolEnd, ToolEvent, ToolStart
from src.alfred import Alfred
from src.cron.notifier import CLINotifier
from src.interfaces.live_display import LiveDisplay
from src.interfaces.notification_buffer import NotificationBuffer
from src.interfaces.status import StatusData
from src.session import Session
from src.theme import Theme
from src.themes import apply_theme, get_theme, list_themes


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
        self.scroll_offset: int = 0  # How many panels hidden from bottom (scroll up)

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up to show older content."""
        max_offset = max(0, len(self.segments) - 1)
        self.scroll_offset = min(self.scroll_offset + lines, max_offset)

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down to show newer content."""
        self.scroll_offset = max(0, self.scroll_offset - lines)

    def scroll_to_bottom(self) -> None:
        """Reset scroll to show newest content."""
        self.scroll_offset = 0

    def scroll_to_top(self) -> None:
        """Scroll to show oldest content."""
        self.scroll_offset = max(0, len(self.segments) - 1)

    def add_user_message(self, content: str) -> None:
        """Add a complete user message as a segment."""
        # Flush any pending assistant text first
        if self._current_text:
            self.segments.append(TextSegment(content=self._current_text, role=self._current_role))
            self._current_text = ""
        self.segments.append(TextSegment(content=content, role="user"))
        self.scroll_offset = 0  # Reset scroll on new content

    def add_system_message(
        self, title: str, content: str, border_style: str = Theme.success
    ) -> None:
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
            self.scroll_offset = 0  # Reset scroll on new content

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
        self.scroll_offset = 0

    def render(self, max_panels: int | None = None) -> list[RenderableType]:
        """Render segments as Rich renderables.

        Args:
            max_panels: Maximum panels to render. None = render all.
        """
        renderables: list[RenderableType] = []

        for segment in self.segments:
            if isinstance(segment, TextSegment) and segment.content:
                renderables.append(self._render_message_panel(segment))
            elif isinstance(segment, ToolCallSegment) and self.panels_visible:
                renderables.append(self._render_tool_panel(segment))

        if self._current_text:
            segment = TextSegment(content=self._current_text, role=self._current_role)
            renderables.append(self._render_message_panel(segment))

        # Apply scroll offset: hide N newest panels to show older ones
        if self.scroll_offset > 0 and len(renderables) > self.scroll_offset:
            renderables = renderables[:-self.scroll_offset]

        # Limit to max_panels from the END (show newest)
        if max_panels is not None and len(renderables) > max_panels:
            renderables = renderables[-max_panels:]

        return renderables

    def render_history(self, max_panels: int | None = None) -> list[RenderableType]:
        """Render completed segments (not streaming text).

        Args:
            max_panels: Maximum panels to render. None = render all.
        """
        renderables: list[RenderableType] = []

        for segment in self.segments:
            if isinstance(segment, TextSegment) and segment.content:
                renderables.append(self._render_message_panel(segment))
            elif isinstance(segment, ToolCallSegment) and self.panels_visible:
                renderables.append(self._render_tool_panel(segment))

        # Apply scroll offset: hide N newest panels to show older ones
        if self.scroll_offset > 0 and len(renderables) > self.scroll_offset:
            renderables = renderables[:-self.scroll_offset]

        # Limit to max_panels from the END (show newest)
        if max_panels is not None and len(renderables) > max_panels:
            renderables = renderables[-max_panels:]

        return renderables

    def render_streaming(self) -> RenderableType:
        """Render the currently streaming message (or empty Text if none)."""
        if self._current_text:
            segment = TextSegment(content=self._current_text, role=self._current_role)
            return self._render_message_panel(segment)
        return Text()

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
        border = Theme.role_user if segment.role == "user" else Theme.role_assistant
        return Panel(
            Markdown(segment.content),
            title=title,
            title_align="left",
            border_style=border,
            padding=(0, 1),
        )

    def _render_tool_panel(self, tool: ToolCallSegment) -> Panel:
        """Render a tool call as a styled Panel."""
        content = self._truncate_result(tool.result, tool.is_error)
        style = Theme.tool_error if tool.is_error else Theme.tool_normal
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
        # Load theme from environment variable before anything else
        theme_config = get_theme()
        apply_theme(theme_config)

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

    def _get_visible_panels(self, renderables: list[RenderableType]) -> list[RenderableType]:
        """Return only panels that fit in terminal, starting from newest.
        
        Measures actual rendered height and keeps newest panels that fit.
        """
        if not renderables:
            return renderables

        terminal_height = self.console.size.height
        available_height = max(terminal_height - 2, 10)  # Reserve for live area
        
        # Measure panels from newest to oldest
        visible: list[RenderableType] = []
        total_height = 0
        
        for renderable in reversed(renderables):
            # Measure this renderable's height
            try:
                height = self.console.render(renderable, self.console.options)
                panel_height = len(list(height))
            except Exception:
                panel_height = 4  # Fallback estimate
            
            if total_height + panel_height > available_height:
                break  # No more room
            
            visible.insert(0, renderable)  # Insert at front to maintain order
            total_height += panel_height
        
        return visible

    def _update_history(self) -> None:
        """Update history display with visible panels."""
        if self._live_display:
            visible = self._get_visible_panels(self.buffer.render())
            self._live_display.set_history(Group(*visible))
            self._live_display.update()
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
        title = Text(
            "Alfred - Your Persistent Memory Assistant",
            style=f"bold {Theme.primary}",
            justify="center",
        )
        banner = Panel(
            title,
            subtitle="exit to quit | compact for memory | Ctrl-T toggle tools",
            border_style=Theme.primary,
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
                    border_style=Theme.role_user,
                    padding=(0, 1),
                )
                self.console.print(panel)
            elif msg.role.value == "assistant":
                panel = Panel(
                    Markdown(msg.content),
                    title="Alfred",
                    title_align="left",
                    border_style=Theme.role_assistant,
                    padding=(0, 1),
                )
                self.console.print(panel)
            elif msg.role.value == "system":
                self.console.print(f"[{Theme.text_secondary} italic][System: {msg.content}][/]")

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
        elif cmd == "/theme":
            return self._cmd_theme(arg)
        return False

    def _cmd_new_session(self) -> bool:
        """Create a new session."""
        session = self.alfred.session_manager.new_session()
        self.buffer.clear()

        # Reset token tracking for new session
        self.alfred.token_tracker.reset()

        # Update context summary for status line
        self.alfred.context_summary.update(
            memories_count=self.alfred.context_summary.memories_count,
            session_messages=0,
        )

        # Add to content area
        self.buffer.add_system_message(
            "New Session Created",
            f"Session ID: [bold {Theme.primary}]{session.meta.session_id}[/]",
            Theme.success,
        )
        if self._live_display:
            self._live_display.set_history(Group(*self.buffer.render()))
            self._live_display.set_status(self._render_status_line())
            self._live_display.update()

        return True

    def _cmd_resume_session(self, session_id: str | None) -> bool:
        """Resume an existing session."""
        if not session_id:
            self.buffer.add_system_message(
                "Error",
                "Usage: /resume <session_id>\nUse /sessions to see available sessions.",
                Theme.error,
            )
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
            return True

        try:
            session = self.alfred.session_manager.resume_session(session_id)
            self.buffer.clear()

            # Restore token counts and context from session history
            msg_count = self.alfred.restore_session_tokens()

            # Update context summary for status line
            self.alfred.context_summary.update(
                memories_count=self.alfred.context_summary.memories_count,
                session_messages=msg_count,
            )

            # Add resume message to content area
            self.buffer.add_system_message(
                "Session Resumed",
                f"Session ID: [bold {Theme.primary}]{session_id}[/]\nMessages: {msg_count}",
                Theme.success,
            )

            # Add conversation history to buffer
            if session.messages:
                for msg in session.messages:
                    if msg.role.value == "user":
                        self.buffer.add_user_message(msg.content)
                    elif msg.role.value == "assistant":
                        self.buffer.add_text(msg.content)
                        self.buffer.finalize_message()

            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()

        except ValueError as e:
            self.buffer.add_system_message("Error", str(e), Theme.error)
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
        return True

    def _cmd_list_sessions(self) -> bool:
        """List all sessions."""
        sessions = self.alfred.session_manager.list_sessions()

        if not sessions:
            self.buffer.add_system_message("Sessions", "No sessions found.", Theme.warning)
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
            return True

        table = Table(title="Sessions", border_style=Theme.border_secondary)
        table.add_column("ID", style=Theme.primary)
        table.add_column("Created", style=Theme.text_secondary)
        table.add_column("Last Active", style=Theme.text_secondary)
        table.add_column("Messages", justify="right")

        current_id = None
        if self.alfred.session_manager.has_active_session():
            current = self.alfred.session_manager.get_current_cli_session()
            if current:
                current_id = current.meta.session_id

        for meta in sessions:
            created = meta.created_at.strftime("%Y-%m-%d %H:%M")
            last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

            id_str = meta.session_id
            if meta.session_id == current_id:
                id_str = f"[bold {Theme.primary}]{meta.session_id}[/] *"

            table.add_row(id_str, created, last_active, str(meta.message_count))

        # Combine buffer content with table in content area
        if self._live_display:
            renderables = self.buffer.render()
            renderables.append(table)
            self._live_display.set_history(Group(*renderables))
            self._live_display.update()
        return True

    def _cmd_show_current_session(self) -> bool:
        """Show current session details."""
        if not self.alfred.session_manager.has_active_session():
            self.buffer.add_system_message("Error", "No active session.", Theme.warning)
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
            return True

        session = self.alfred.session_manager.get_current_cli_session()
        if not session:
            self.buffer.add_system_message("Error", "No active session.", Theme.warning)
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
            return True

        meta = session.meta
        created = meta.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

        panel = Panel(
            f"ID: [bold {Theme.primary}]{meta.session_id}[/]\n"
            f"Status: {meta.status}\n"
            f"Created: {created}\n"
            f"Last Active: {last_active}\n"
            f"Messages: {meta.message_count}",
            title="Current Session",
            border_style=Theme.primary,
        )

        # Add to content area
        if self._live_display:
            renderables = self.buffer.render()
            renderables.append(panel)
            self._live_display.set_history(Group(*renderables))
            self._live_display.update()
        return True

    def _cmd_theme(self, theme_name: str | None) -> bool:
        """Show or change the current theme."""
        if theme_name is None:
            # Show current theme and available options
            import os

            from src.themes import THEMES

            current = os.environ.get("ALFRED_THEME", "dark")

            table = Table(title="Available Themes", border_style=Theme.border_secondary)
            table.add_column("Name", style=Theme.primary)
            table.add_column("Status", style=Theme.text_secondary)

            for name in sorted(THEMES.keys()):
                status = "current" if name == current else ""
                table.add_row(name, status)

            if self._live_display:
                renderables = self.buffer.render()
                renderables.append(table)
                renderables.append(Text("\nUsage: /theme <name>"))
                renderables.append(Text("Set ALFRED_THEME env var to change default"))
                self._live_display.set_history(Group(*renderables))
                self._live_display.update()
            return True

        # Try to apply the theme
        theme_name = theme_name.lower().strip()
        available = list_themes()

        if theme_name not in available:
            self.buffer.add_system_message(
                "Error",
                f"Unknown theme: {theme_name}\nAvailable: {', '.join(sorted(available))}",
                Theme.error,
            )
            if self._live_display:
                self._live_display.set_history(Group(*self.buffer.render()))
                self._live_display.update()
            return True

        # Apply the theme
        theme_config = get_theme(theme_name)
        apply_theme(theme_config)

        self.buffer.add_system_message(
            "Theme Applied",
            f"Theme changed to: [bold {Theme.primary}]{theme_name}[/]\n"
            f"Note: Set ALFRED_THEME={theme_name} to persist.",
            Theme.success,
        )
        if self._live_display:
            self._live_display.set_history(Group(*self.buffer.render()))
            self._live_display.update()
        return True

    async def run(self) -> None:
        """Main CLI loop."""
        # Print banner to scrollback (outside Live display)
        self._print_banner()

        # Load session history into buffer for content area display
        if self.alfred.session_manager.has_active_session():
            session = self.alfred.session_manager.get_current_cli_session()
            if session:
                # Restore token counts and context from session history
                msg_count = self.alfred.restore_session_tokens()

                # Update context summary for status line
                self.alfred.context_summary.update(
                    memories_count=self.alfred.context_summary.memories_count,
                    session_messages=msg_count,
                )

                # Load conversation history into buffer for content area
                if session.messages:
                    for msg in session.messages:
                        if msg.role.value == "user":
                            self.buffer.add_user_message(msg.content)
                        elif msg.role.value == "assistant":
                            self.buffer.add_text(msg.content)
                            self.buffer.finalize_message()

        # Create callback for session ID completion
        def get_session_ids() -> list[str]:
            return [meta.session_id for meta in self.alfred.session_manager.list_sessions()]

        # Create scroll callback for mouse wheel
        def on_scroll(direction: int) -> None:
            """Handle scroll events. direction: 1=up, -1=down."""
            if direction > 0:
                self.buffer.scroll_up()
            else:
                self.buffer.scroll_down()
            # Refresh display with new scroll position
            if self._live_display:
                visible = self._get_visible_panels(self.buffer.render())
                self._live_display.set_history(Group(*visible))
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()

        # Create LiveDisplay
        self._live_display = LiveDisplay(
            console=self.console,
            history_path=self._get_history_path(),
            get_session_ids=get_session_ids,
            on_scroll=on_scroll,
        )

        # Set initial content and status BEFORE entering context
        if self.buffer.segments:
            self._live_display.set_history(Group(*self.buffer.render()))
        self._live_display.set_status(self._render_status_line())

        with self._live_display:
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
                    self.console.print(f"[bold {Theme.warning}]Goodbye![/]")
                    break

                if user_input.lower() == "compact":
                    result = await self.alfred.compact()
                    self.buffer.add_system_message("Compact", result, Theme.success)
                    if self._live_display:
                        self._live_display.set_history(Group(*self.buffer.render()))
                        self._live_display.update()
                    continue

                # Handle Ctrl+T toggle (as command for now)
                if user_input.lower() == "/toggle":
                    self.buffer.toggle_panels()
                    state = "visible" if self.buffer.panels_visible else "hidden"
                    self.buffer.add_system_message(
                        "Tool Panels", f"Tool panels: {state}", Theme.text_secondary
                    )
                    if self._live_display:
                        self._live_display.set_history(Group(*self.buffer.render()))
                        self._live_display.update()
                    continue

                # Session commands
                if user_input.startswith("/") and self._handle_session_command(user_input):
                    continue

                # Stream response - set streaming state FIRST for throbber
                self._is_streaming = True
                if self._live_display:
                    self._live_display.set_status(self._render_status_line())
                    self._live_display.update()
                await self._stream_response(user_input)

    async def _stream_response(self, user_input: str) -> None:
        """Stream a response from Alfred."""
        # Add user message to buffer (goes to history)
        self.buffer.add_user_message(user_input)

        # Disable echo during streaming
        if self._live_display:
            self._live_display.disable_echo()

        try:
            async for chunk in self.alfred.chat_stream(
                user_input,
                tool_callback=self._on_tool_event,
            ):
                self.buffer.add_text(chunk)

                # Update history (completed segments) and streaming (current text)
                if self._live_display:
                    visible = self._get_visible_panels(self.buffer.render_history())
                    self._live_display.set_history(Group(*visible))
                    self._live_display.set_streaming(self.buffer.render_streaming())
                    self._live_display.set_status(self._render_status_line())
                    self._live_display.update()

            # Finalize the assistant message
            self.buffer.finalize_message()

            rendered = self._get_visible_panels(self.buffer.render())

            # Update history with completed message, clear streaming area
            if self._live_display:
                self._live_display.set_history(Group(*rendered))
                self._live_display.clear_streaming()
                self._live_display.update()

        except Exception as e:
            self.console.print(f"\n[bold {Theme.error}]Error: {e}[/]\n")
        finally:
            self._is_streaming = False
            if self._live_display:
                self._live_display.set_status(self._render_status_line())
                self._live_display.update()
                self._live_display.enable_echo()
            self._flush_notifications()

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
        text.append(status_data.model_name, style=f"bold {Theme.primary}")
        text.append(" | ", style=Theme.text_secondary)

        # Token counts
        text.append(f"in:{self._format_number(usage.input_tokens)} ", style=Theme.metric_input)
        text.append(f"out:{self._format_number(usage.output_tokens)}", style=Theme.metric_output)
        if usage.cache_read_tokens > 0:
            cache = self._format_number(usage.cache_read_tokens)
            text.append(f" cache:{cache}", style=Theme.metric_cache)
        if usage.reasoning_tokens > 0:
            reason = self._format_number(usage.reasoning_tokens)
            text.append(f" reason:{reason}", style=Theme.metric_reasoning)

        # Context percentage
        ctx = self._format_number(status_data.context_tokens)
        text.append(f" | ctx:{ctx}", style=Theme.text_secondary)

        # Memory and message counts
        m = status_data.memories_count
        s = status_data.session_messages
        text.append(f"  📚 {m} | 💬 {s}", style=Theme.text_primary)

        # Scroll position indicator (only show when scrolled)
        if self.buffer.scroll_offset > 0:
            total = len(self.buffer.segments)
            visible_from_bottom = self.buffer.scroll_offset
            text.append(f" ⬆ {visible_from_bottom}/{total}", style=Theme.warning)

        # Throbber: animated spinner when streaming, static ">" when idle
        if self._is_streaming:
            from rich.columns import Columns
            spinner = Spinner("dots", style=Theme.spinner)
            return Columns([spinner, text])
        else:
            prefix = Text("> ", style=Theme.prompt)
            prefix.append(text)
            return prefix

    @staticmethod
    def _format_number(n: int) -> str:
        """Format number with K suffix for thousands."""
        if n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(n)

    def _flush_notifications(self) -> None:
        """Flush queued notifications to content area."""
        if not self._notification_buffer or not self._notification_buffer.has_pending():
            return

        notifications = self._notification_buffer.flush()
        if not notifications:
            return

        # Build notification display
        lines: list[str] = []
        lines.append(f"{'─' * 20} Jobs ({len(notifications)}) {'─' * 20}")
        for notification in notifications:
            ts = notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{ts}] {notification.message}")
        lines.append(f"{'─' * 52}")

        # Add to buffer as system message
        self.buffer.add_system_message(
            "Job Notifications",
            "\n".join(lines),
            Theme.text_secondary,
        )

        if self._live_display:
            self._live_display.set_history(Group(*self.buffer.render()))
            self._live_display.update()
