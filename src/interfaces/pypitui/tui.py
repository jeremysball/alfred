"""Main AlfredTUI class for the CLI interface."""

import asyncio
import logging
import signal
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from pypitui import TUI, Container, Key, OverlayOptions, matches_key

from src.alfred import Alfred

logger = logging.getLogger(__name__)

# Import commands
from src.interfaces.pypitui.commands import (
    Command,
    ListSessionsCommand,
    NewSessionCommand,
    ResumeSessionCommand,
    ShowContextCommand,
    ShowSessionCommand,
)
from src.interfaces.pypitui.completion_menu_component import CompletionMenuComponent

# Settings now accessed via self.alfred.config
from src.interfaces.pypitui.fuzzy import fuzzy_match
from src.interfaces.pypitui.message_panel import MessagePanel
from src.interfaces.pypitui.models import ToolCallInfo
from src.interfaces.pypitui.status_line import StatusLine
from src.interfaces.pypitui.toast import ToastManager
from src.interfaces.pypitui.toast_overlay import ToastOverlay
from src.interfaces.pypitui.wrapped_input import WrappedInput
from src.session import ToolCallRecord

if TYPE_CHECKING:
    from pypitui import OverlayHandle, ProcessTerminal


class AlfredTUI:
    """Main TUI class for Alfred CLI using PyPiTUI."""

    def __init__(
        self,
        alfred: Alfred,
        terminal: "ProcessTerminal | None" = None,
        toast_manager: ToastManager | None = None,
    ) -> None:
        """Initialize the Alfred TUI.

        Args:
            alfred: The Alfred instance to interact with
            terminal: Optional terminal to use (for testing)
            toast_manager: Optional ToastManager for notifications
        """
        from pypitui import ProcessTerminal

        self.alfred = alfred
        self.terminal = terminal or ProcessTerminal()
        self.tui = TUI(self.terminal)
        self.tui.on_resize = self._on_resize
        self._toast_manager = toast_manager

        # Main conversation container
        self.conversation = Container()

        # Status line for model/token info
        self.status_line = StatusLine()

        # Completion menu as proper component (renders empty when closed)
        self.completion_menu = CompletionMenuComponent(max_height=10)

        # Input field for user messages (with wrapped text navigation and completion)
        cursor_color = getattr(alfred.config, "input_cursor_color", "reverse")
        self.input_field = WrappedInput(placeholder="Message Alfred...", cursor_color=cursor_color)
        self.input_field.on_submit = self._on_submit

        # Wire up completion with multiple triggers (longest match wins)
        completion = self.input_field.setup_completion(self.completion_menu)
        completion.register("/", self._command_provider)
        completion.register("/resume ", self._session_id_provider)

        # Build layout: conversation (flex), status, completion menu, input
        self.tui.add_child(self.conversation)
        self.tui.add_child(self.status_line)
        self.tui.add_child(self.completion_menu)
        self.tui.add_child(self.input_field)
        self.tui.set_focus(self.input_field)

        # Toast overlay (non-modal popup at bottom of screen)
        self._toast_overlay: ToastOverlay | None = None
        self._toast_handle: OverlayHandle | None = None
        if toast_manager is not None:
            self._toast_overlay = ToastOverlay(toast_manager)

        # State
        self.running = True
        self._terminal_width: int = 80  # Default width

        # Ctrl-C state
        self._ctrl_c_pending = False

        # SIGWINCH state - flag set when window resize signal received
        self._resize_pending = False

        # Current assistant message for inline tool calls
        self._current_assistant_msg: MessagePanel | None = None

        # Input queue for messages during streaming
        self._message_queue: list[str] = []
        self._is_streaming = False
        self._is_sending = False  # True while waiting for first chunk

        # Queue navigation state (for UP/DOWN arrow history)
        self._queue_nav_index: int = -1  # -1 = not navigating, 0+ = index in queue
        self._queue_draft: str = ""  # Saved draft when navigating queue

        # Command registry - explicit registration
        self._commands: dict[str, Command] = {
            "/new": NewSessionCommand(),
            "/resume": ResumeSessionCommand(),
            "/sessions": ListSessionsCommand(),
            "/session": ShowSessionCommand(),
            "/context": ShowContextCommand(),
        }

        # Toast manager is passed directly, no need to configure through notifier
        # Socket-based cron runner sends notifications via Unix socket

        # Add input listener for queue navigation (ESC to cancel, UP/DOWN for history)
        self.tui.add_input_listener(self._input_listener)

        # Initialize status line with current values
        self._update_status()

        # Set up SIGWINCH handler for terminal resize
        self._setup_sigwinch_handler()

    def _setup_sigwinch_handler(self) -> None:
        """Set up SIGWINCH handler to detect terminal resize immediately."""
        def handle_sigwinch(signum: int, frame: object) -> None:
            """Signal handler - just set flag, actual handling happens in main loop."""
            self._resize_pending = True

        with suppress(AttributeError, ValueError):
            signal.signal(signal.SIGWINCH, handle_sigwinch)

    def _handle_resize(self) -> None:
        """Handle pending resize by updating PyPiTUI cache and Alfred components."""
        self._resize_pending = False
        # Update PyPiTUI's cached size (so render_frame doesn't call get_size)
        self.tui.request_resize_check()
        # Get new size for Alfred components
        term_width, term_height = self.terminal.get_size()
        self._terminal_width = term_width
        # Update message panels with new width
        self._on_resize(term_width, term_height)
        # Force full redraw
        self.tui.request_render(force=True)

    def _handle_ctrl_c(self) -> None:
        """Handle Ctrl-C keypress.

        If input is empty: exit immediately.
        First Ctrl-C with input: clear input, show toast hint.
        Second Ctrl-C: exit.
        """
        # Exit immediately if input is empty
        if not self.input_field.get_value().strip():
            self.running = False
            return

        if self._ctrl_c_pending:
            # Second Ctrl-C - exit
            self.running = False
        else:
            # First Ctrl-C - clear input and show toast hint
            self.input_field.set_value("")
            self._ctrl_c_pending = True
            # Show toast instead of status line hint
            if self._toast_manager is not None:
                self._toast_manager.add(
                    "Press Ctrl-C again to exit",
                    level="info",
                )

    def _reset_ctrl_c_state(self) -> None:
        """Reset Ctrl-C pending state and dismiss toasts (called on any other key)."""
        self._ctrl_c_pending = False
        # Dismiss any visible toasts on keypress
        if self._toast_manager is not None:
            self._toast_manager.dismiss_all()

    def _update_toast_overlay(self) -> None:
        """Update toast overlay visibility based on current toasts.

        Shows overlay when toasts exist, hides when empty.
        Overlay is non-modal (doesn't affect focus).
        """
        if self._toast_overlay is None:
            return

        has_toasts = self._toast_overlay.has_toasts()

        if has_toasts and self._toast_handle is None:
            # Show toast overlay at bottom-left, non-modal
            options = OverlayOptions(
                anchor="bottom-left",
                offset_y=-2,  # 2 lines from bottom (above input)
                margin=2,  # Left margin
            )
            self._toast_handle = self.tui.show_overlay(self._toast_overlay, options)
        elif not has_toasts and self._toast_handle is not None:
            # Hide toast overlay only if it's not already hidden
            if not self._toast_handle.is_hidden():
                self._toast_handle.hide()
            self._toast_handle = None

    def _update_status(self, estimated_out: int | None = None) -> None:
        """Update status line with current token counts.

        Args:
            estimated_out: Estimated output tokens during streaming.
                           If None, uses actual from token_tracker.
        """
        usage = self.alfred.token_tracker.usage
        ctx = self.alfred.token_tracker.context_tokens

        # Use estimated during stream, actual after
        out = estimated_out if estimated_out is not None else usage.output_tokens

        self.status_line.update(
            model=self.alfred.model_name,
            ctx=ctx,
            in_tokens=usage.input_tokens,
            out_tokens=out,
            cached=usage.cache_read_tokens,
            reasoning=usage.reasoning_tokens,
            queued=len(self._message_queue),
            streaming=self._is_streaming or self._is_sending,
        )

    def _on_resize(self, term_width: int, term_height: int) -> None:
        """Handle terminal resize by re-populating scrollback if needed."""
        # Update terminal width for message panels
        self._terminal_width = term_width

        # Update all message panels with new width
        for child in self.conversation.children:
            if hasattr(child, "set_terminal_width"):
                child.set_terminal_width(term_width)

        # Re-populate scrollback if there's overflow content
        self._populate_scrollback_by_scrolling()

    def _calculate_static_height(self) -> int:
        """Calculate total height of fixed (non-scrollable) UI components.

        Walks from bottom to top, summing heights of static components.
        This includes: status_line, completion_menu (if open), input_field.

        Returns:
            Total height in terminal rows occupied by fixed components.
        """
        static_height = 0

        # Input field (always visible at bottom)
        # WrappedInput renders at least 1 line, more if text wraps
        input_lines = len(self.input_field.render(self._terminal_width))
        static_height += input_lines

        # Completion menu (conditional, above input)
        if self.completion_menu.is_open:
            menu_lines = len(self.completion_menu.render(self._terminal_width))
            static_height += menu_lines

        # Status line (always visible, above completion menu)
        status_lines = len(self.status_line.render(self._terminal_width))
        static_height += status_lines

        return static_height

    def _input_listener(self, data: str) -> dict | None:
        """Intercept input for queue navigation and cancellation.

        Returns:
            {"consume": True} to block input from reaching input field,
            None to allow input to pass through.
        """
        from pypitui import Key

        # ESC clears the queue
        if matches_key(data, Key.escape):
            if self._message_queue:
                self._message_queue.clear()
                self._queue_nav_index = -1
                self._queue_draft = ""
                self.input_field.set_value("")
                self._update_status()
                return {"consume": True}
            return None

        # UP arrow on first line -> enter queue history or navigate up
        if matches_key(data, Key.up):
            cursor_line = self._get_input_cursor_line()
            if cursor_line == 0 and self._message_queue:
                if self._queue_nav_index == -1:
                    # Save current draft and enter queue at end
                    self._queue_draft = self.input_field.get_value()
                    self._queue_nav_index = len(self._message_queue) - 1
                elif self._queue_nav_index > 0:
                    # Navigate up in queue
                    self._queue_nav_index -= 1
                else:
                    return {"consume": True}  # Already at top

                self.input_field.set_value(self._message_queue[self._queue_nav_index])
                return {"consume": True}
            return None

        # DOWN arrow -> navigate down in queue or exit to draft
        if matches_key(data, Key.down):
            if self._queue_nav_index != -1:
                if self._queue_nav_index < len(self._message_queue) - 1:
                    # Navigate down in queue
                    self._queue_nav_index += 1
                    self.input_field.set_value(self._message_queue[self._queue_nav_index])
                else:
                    # Exit queue nav, restore draft
                    self._queue_nav_index = -1
                    self.input_field.set_value(self._queue_draft)
                return {"consume": True}
            return None

        # Any other key resets queue navigation
        if self._queue_nav_index != -1:
            self._queue_nav_index = -1
            self._queue_draft = ""

        return None

    def _get_input_cursor_line(self) -> int:
        """Get which display line the cursor is on (0-indexed)."""
        width = self.terminal.get_size()[0]
        if width <= 0:
            return 0
        cursor_pos = self.input_field._cursor_pos
        return cursor_pos // width

    def _ensure_assistant_message(self) -> MessagePanel:
        """Create assistant message panel if it doesn't exist yet.

        Returns:
            The assistant message panel (existing or newly created).
        """
        if self._current_assistant_msg is None:
            # Create assistant message panel
            self._current_assistant_msg = MessagePanel(
                role="assistant",
                content="",
                terminal_width=self._terminal_width,
                use_markdown=self.alfred.config.use_markdown_rendering,
            )
            self.conversation.add_child(self._current_assistant_msg)
            self.tui.request_render()
        return self._current_assistant_msg

    def _tool_callback(self, event: object) -> None:
        """Handle tool execution events - embed in current assistant message.

        Args:
            event: ToolStart, ToolOutput, or ToolEnd from agent
        """
        from src.agent import ToolEnd, ToolOutput, ToolStart

        # Ensure message panel exists (create on first tool event if needed)
        assistant_msg = self._ensure_assistant_message()

        if isinstance(event, ToolStart):
            # Add tool call to current message at current position
            assistant_msg.add_tool_call(event.tool_name, event.tool_call_id, event.arguments)

        elif isinstance(event, ToolOutput):
            # Append output to existing tool call
            assistant_msg.update_tool_call(event.tool_call_id, event.chunk)

        elif isinstance(event, ToolEnd):
            # Set final status
            status: Literal["success", "error"] = "error" if event.is_error else "success"
            assistant_msg.finalize_tool_call(event.tool_call_id, status)

        # Request re-render
        self.tui.request_render()

    def _on_submit(self, text: str) -> None:
        """Handle user input submission.

        Args:
            text: The submitted text
        """
        # NOTE: Input field is already cleared by WrappedInput._on_submit
        # before this method is called, to prevent race conditions.

        # Strip whitespace and ignore empty
        text = text.strip()
        if not text:
            return

        # If currently streaming, queue the message
        if self._is_streaming:
            self._message_queue.append(text)
            self._update_status()
            return

        # Check for session commands
        if text.startswith("/") and self._handle_session_command(text):
            return

        # Add user message to conversation
        user_msg = MessagePanel(
            role="user",
            content=text,
            terminal_width=self._terminal_width,
            use_markdown=self.alfred.config.use_markdown_rendering,
        )
        self.conversation.add_child(user_msg)

        # Start sending state immediately for throbber feedback
        self._is_sending = True
        self._update_status()

        # Create async task for response (requires running event loop)
        with suppress(RuntimeError):
            asyncio.create_task(self._send_message(text))

    def _handle_session_command(self, text: str) -> bool:
        """Handle session commands. Returns True if handled."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if cmd in self._commands:
            return self._commands[cmd].execute(self, arg)
        return False

    def _command_provider(self, text: str) -> list[tuple[str, str | None]]:
        """Provide command completions for '/' trigger.

        Args:
            text: Current input text.

        Returns:
            List of (command, description) tuples matching the text.
        """
        if not text.startswith("/"):
            return []

        # Available commands with descriptions
        commands = [
            ("/new", "Create new session"),
            ("/resume", "Resume session by ID"),
            ("/sessions", "List all sessions"),
            ("/session", "Show current session info"),
            ("/context", "Show system context"),
        ]

        # Filter by fuzzy match
        return [(cmd, desc) for cmd, desc in commands if fuzzy_match(text, cmd)]

    def _session_id_provider(self, text: str) -> list[tuple[str, str | None]]:
        """Provide session ID completions for '/resume ' trigger.

        Args:
            text: Current input text (e.g., '/resume abc').

        Returns:
            List of (session_id, description) tuples matching the text.
        """
        if not text.startswith("/resume "):
            return []

        # Get the partial ID being typed
        partial = text[8:]  # After '/resume '

        # Get available session IDs (list of strings)
        session_ids = self.alfred.session_manager.storage.list_sessions()
        sessions_with_meta = []

        for sid in session_ids:
            # Fuzzy match against partial ID
            if not fuzzy_match(partial.lower(), sid.lower()):
                continue

            # Get metadata for date and message count
            meta = self.alfred.session_manager.storage.get_meta(sid)
            if meta:
                # Format: "Mar 3 21:45 · 12 msgs"
                date_str = meta.last_active.strftime("%b %-d %H:%M")
                msg_count = meta.current_count + meta.archive_count
                desc = f"{date_str} · {msg_count} msgs"
                sessions_with_meta.append((sid, desc, meta.last_active))
            else:
                # No metadata, use placeholder
                sessions_with_meta.append((sid, None, datetime.min.replace(tzinfo=UTC)))

        # Sort by last_active descending (most recent first)
        sessions_with_meta.sort(key=lambda x: x[2], reverse=True)

        # Limit to 5 results for usability
        sessions_with_meta = sessions_with_meta[:5]

        # Return (completion_value, description) tuples
        return [(f"/resume {sid}", desc) for sid, desc, _ in sessions_with_meta]

    def _clear_conversation(self) -> None:
        """Clear all messages from the conversation."""
        self.conversation.clear()
        # Clear terminal screen and reset scrollback tracking.
        # This ensures old content is gone before loading resumed session.
        self.tui.terminal.write("\x1b[2J\x1b[H")
        self.tui.reset_scrollback_state()

    @staticmethod
    def _convert_tool_call_record(record: ToolCallRecord) -> ToolCallInfo:
        """Convert a ToolCallRecord to ToolCallInfo for display.

        Args:
            record: ToolCallRecord from session storage

        Returns:
            ToolCallInfo for display in MessagePanel
        """
        return ToolCallInfo(
            tool_name=record.tool_name,
            tool_call_id=record.tool_call_id,
            insert_position=record.insert_position,
            sequence=record.sequence,
            arguments=record.arguments,
            output=record.output,
            # ToolCallRecord uses "success"/"error", ToolCallInfo accepts these
            status=record.status,
        )

    @staticmethod
    def _convert_tool_calls(
        records: list[ToolCallRecord] | None,
    ) -> list[ToolCallInfo] | None:
        """Convert a list of ToolCallRecords to ToolCallInfos.

        Args:
            records: List of ToolCallRecords from session storage, or None

        Returns:
            List of ToolCallInfos for display, or None if input was None
        """
        if records is None:
            return None
        return [AlfredTUI._convert_tool_call_record(r) for r in records]

    def _load_session_messages(self) -> None:
        """Load existing session messages into conversation panel.

        Called on startup (if resuming) and after /resume command.
        Renders all historical messages as MessagePanels.

        Sets scrollback position so older messages flow into terminal
        scrollback history instead of all being rendered on screen.
        """
        if not self.alfred.session_manager.has_active_session():
            return

        session = self.alfred.session_manager.get_current_cli_session()
        if not session or not session.messages:
            return

        # Add all message panels to conversation
        for msg in session.messages:
            # Convert stored tool calls to ToolCallInfo for display
            tool_calls = self._convert_tool_calls(msg.tool_calls)

            panel = MessagePanel(
                role=msg.role.value,
                content=msg.content,
                terminal_width=self._terminal_width,
                use_markdown=self.alfred.config.use_markdown_rendering,
                tool_calls=tool_calls,
            )
            self.conversation.add_child(panel)

        # Sync token tracker with loaded session messages
        self.alfred.sync_token_tracker_from_session()

        # Populate scrollback: render screenfuls and scroll them into history
        self._populate_scrollback_by_scrolling()

        self.tui.request_render()

    def _populate_scrollback_by_scrolling(self) -> None:
        """Populate terminal scrollback by rendering and scrolling content.

        To get content into the terminal's scrollback buffer, we need to:
        1. Render a screenful of content (oldest content first)
        2. Use SU (Scroll Up) to push it into scrollback
        3. Repeat until all old content is in scrollback
        4. Leave recent content for normal absolute-position render
        """
        term_width, term_height = self.tui.terminal.get_size()
        self._terminal_width = term_width  # Update cached width
        static_height = self._calculate_static_height()
        scrollable_height = max(1, term_height - static_height)

        # Get rendered conversation lines
        content_lines = self.conversation.render(term_width)

        if len(content_lines) <= scrollable_height:
            return  # Content fits, no scrollback needed

        # Lines that should go into scrollback
        lines_for_scrollback = len(content_lines) - scrollable_height

        buffer = "\x1b[?2026h"  # Begin sync

        # Set scroll region to protect static components
        buffer += f"\x1b[1;{scrollable_height}r"

        # Process scrollback content in screen-sized chunks
        # Render a screenful, then scroll it all into scrollback
        scrollback_content = content_lines[:lines_for_scrollback]
        pos = 0

        while pos < len(scrollback_content):
            # Get next screenful of content
            chunk = scrollback_content[pos : pos + scrollable_height]

            # Render this chunk at absolute positions
            for i, line in enumerate(chunk):
                buffer += f"\x1b[{i + 1};1H"  # Position cursor
                buffer += "\x1b[2K"  # Clear line
                buffer += line

            # Scroll this chunk into scrollback
            buffer += f"\x1b[{len(chunk)}S"

            pos += len(chunk)

        buffer += "\x1b[r"  # Reset scroll region
        buffer += "\x1b[?2026l"  # End sync

        self.tui.terminal.write(buffer)

        # Track scrollback position to avoid re-rendering
        self._scrollback_position = lines_for_scrollback

    def _add_user_message(self, content: str) -> None:
        """Add a user message panel to the conversation."""
        msg = MessagePanel(
            role="user",
            content=content,
            terminal_width=self._terminal_width,
            use_markdown=self.alfred.config.use_markdown_rendering,
        )
        self.conversation.add_child(msg)
        self.tui.request_render()

    def _add_system_message(self, content: str) -> None:
        """Add a system message panel to the conversation.

        System messages are displayed with 'System' role and do not use
        markdown rendering to preserve their pre-formatted output.
        """
        msg = MessagePanel(
            role="system",
            content=content,
            terminal_width=self._terminal_width,
            use_markdown=False,  # Disable markdown to preserve formatting
        )
        self.conversation.add_child(msg)
        self.tui.request_render()

    async def _send_message(self, text: str) -> None:
        """Send message to Alfred and handle response.

        Args:
            text: The user message
        """
        # Mark as streaming (is_sending was already set in _on_submit)
        self._is_streaming = True

        # Don't create assistant message panel yet - wait for first chunk or tool call
        first_chunk = True
        next_to_process: str | None = None
        try:
            # Stream response from Alfred
            accumulated = ""
            async for chunk in self.alfred.chat_stream(text, tool_callback=self._tool_callback):
                # Create message panel on first chunk
                if first_chunk:
                    self._is_sending = False
                    first_chunk = False
                    # Create panel now that content is arriving
                    self._ensure_assistant_message()

                # Panel is guaranteed to exist now (either created above or by tool callback)
                assert self._current_assistant_msg is not None
                accumulated += chunk
                self._current_assistant_msg.set_content(accumulated)

                # Estimate output tokens during streaming (chars / 4)
                estimated_out = len(accumulated) // 4
                self._update_status(estimated_out=estimated_out)

                self.tui.request_render()

            # Final update with actual token counts (only if panel exists)
            if self._current_assistant_msg is not None:
                self._update_status()
        except Exception as e:
            # Ensure panel exists to show error
            assistant_msg = self._ensure_assistant_message()
            # Show error in panel with red border
            assistant_msg.set_error(str(e))
            self._update_status()
            self.tui.request_render()
        finally:
            self._current_assistant_msg = None
            self._is_streaming = False
            self._is_sending = False
            self._update_status()

            # Grab next queued message if any (process after finally)
            if self._message_queue:
                next_to_process = self._message_queue.pop(0)

        # Process queued message outside finally block
        if next_to_process is not None:
            # Check if it's a session command
            if next_to_process.startswith("/") and self._handle_session_command(next_to_process):
                return  # Command handled, don't send to LLM

            # Add user message and send to LLM
            user_msg = MessagePanel(
                role="user",
                content=next_to_process,
                terminal_width=self._terminal_width,
                use_markdown=self.alfred.config.use_markdown_rendering,
            )
            self.conversation.add_child(user_msg)
            self._update_status()
            asyncio.create_task(self._send_message(next_to_process))

    async def run(self) -> None:
        """Main event loop - reads input, handles events, renders frames."""
        self.tui.start()
        logger.debug("TUI started")

        # Load existing session messages on startup
        self._load_session_messages()

        # Update status line with current session state
        self._update_status()

        try:
            while self.running:
                # Handle pending resize from SIGWINCH
                if self._resize_pending:
                    logger.debug("Handling resize")
                    self._handle_resize()

                # Read terminal input with timeout
                try:
                    data = self.terminal.read_sequence(timeout=0.01)
                    if data:
                        logger.debug(f"Input received: {repr(data)}")
                        # Check for Ctrl+C
                        if matches_key(data, Key.ctrl("c")):
                            self._handle_ctrl_c()
                            if not self.running:
                                break  # Second Ctrl-C, exit loop
                        else:
                            # Any other key resets Ctrl-C state
                            if self._ctrl_c_pending:
                                self._reset_ctrl_c_state()
                            self.tui.handle_input(data)
                except Exception as e:
                    logger.debug(f"Input error: {e}")

                # Update toast overlay visibility
                self._update_toast_overlay()

                # Animate throbber during streaming
                self.status_line.tick_throbber()

                # Render frame
                self.tui.request_render()
                try:
                    self.tui.render_frame()
                except Exception:
                    logger.exception("Render error")

                # Yield to event loop (~60fps)
                await asyncio.sleep(0.016)
        except Exception:
            logger.exception("Main loop error")
            raise
        finally:
            logger.debug("TUI stopping")
            # Clear screen and reset cursor before exit
            self.terminal.write("\x1b[2J\x1b[H\x1b[?25h")
            self.tui.stop()
