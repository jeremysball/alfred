"""Main AlfredTUI class for the CLI interface."""

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Literal

from pypitui import Container, Key, OverlayOptions, matches_key

from src.alfred import Alfred
from src.interfaces.pypitui.message_panel import MessagePanel
from src.interfaces.pypitui.patched_tui import PatchedTUI
from src.interfaces.pypitui.status_line import StatusLine
from src.interfaces.pypitui.toast import ToastManager
from src.interfaces.pypitui.toast_overlay import ToastOverlay
from src.interfaces.pypitui.wrapped_input import WrappedInput

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
        self.tui = PatchedTUI(self.terminal)
        self._toast_manager = toast_manager

        # Main conversation container
        self.conversation = Container()

        # Status line for model/token info
        self.status_line = StatusLine()

        # Input field for user messages (with wrapped text navigation)
        self.input_field = WrappedInput(placeholder="Message Alfred...")
        self.input_field.on_submit = self._on_submit

        # Build layout: conversation (flex), status, input
        self.tui.add_child(self.conversation)
        self.tui.add_child(self.status_line)
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

        # Current assistant message for inline tool calls
        self._current_assistant_msg: MessagePanel | None = None

        # Input queue for messages during streaming
        self._message_queue: list[str] = []
        self._is_streaming = False
        self._is_sending = False  # True while waiting for first chunk

        # Queue navigation state (for UP/DOWN arrow history)
        self._queue_nav_index: int = -1  # -1 = not navigating, 0+ = index in queue
        self._queue_draft: str = ""  # Saved draft when navigating queue

        # Enable toast mode for cron job notifications
        if toast_manager is not None:
            from src.cron.notifier import CLINotifier

            if isinstance(self.alfred.notifier, CLINotifier):
                self.alfred.notifier.set_toast_manager(toast_manager)

        # Add input listener for queue navigation (ESC to cancel, UP/DOWN for history)
        self.tui.add_input_listener(self._input_listener)

        # Initialize status line with current values
        self._update_status()

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
            # Hide toast overlay
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

                self.input_field.set_value(
                    self._message_queue[self._queue_nav_index]
                )
                return {"consume": True}
            return None

        # DOWN arrow -> navigate down in queue or exit to draft
        if matches_key(data, Key.down):
            if self._queue_nav_index != -1:
                if self._queue_nav_index < len(self._message_queue) - 1:
                    # Navigate down in queue
                    self._queue_nav_index += 1
                    self.input_field.set_value(
                        self._message_queue[self._queue_nav_index]
                    )
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

    def _tool_callback(self, event: object) -> None:
        """Handle tool execution events - embed in current assistant message.

        Args:
            event: ToolStart, ToolOutput, or ToolEnd from agent
        """
        from src.agent import ToolEnd, ToolOutput, ToolStart

        if self._current_assistant_msg is None:
            return  # No message to embed into

        if isinstance(event, ToolStart):
            # Add tool call to current message at current position
            self._current_assistant_msg.add_tool_call(
                event.tool_name, event.tool_call_id
            )

        elif isinstance(event, ToolOutput):
            # Append output to existing tool call
            self._current_assistant_msg.update_tool_call(
                event.tool_call_id, event.chunk
            )

        elif isinstance(event, ToolEnd):
            # Set final status
            status: Literal["success", "error"] = "error" if event.is_error else "success"
            self._current_assistant_msg.finalize_tool_call(event.tool_call_id, status)

        # Request re-render
        self.tui.request_render()

    def _on_submit(self, text: str) -> None:
        """Handle user input submission.

        Args:
            text: The submitted text
        """
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
            self.input_field.set_value("")
            return

        # Add user message to conversation
        user_msg = MessagePanel(role="user", content=text, terminal_width=self._terminal_width)
        self.conversation.add_child(user_msg)

        # Clear input field
        self.input_field.set_value("")

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

        if cmd == "/new":
            return self._cmd_new_session()
        elif cmd == "/resume":
            return self._cmd_resume_session(arg)
        elif cmd == "/sessions":
            return self._cmd_list_sessions()
        elif cmd == "/session":
            return self._cmd_show_current_session()
        return False

    def _clear_conversation(self) -> None:
        """Clear all messages from the conversation."""
        self.conversation.clear()
        self.tui.request_render(force=True)

    def _load_session_messages(self) -> None:
        """Load existing session messages into conversation panel.

        Called on startup (if resuming) and after /resume command.
        Renders all historical messages as MessagePanels.
        """
        if not self.alfred.session_manager.has_active_session():
            return

        session = self.alfred.session_manager.get_current_cli_session()
        if not session or not session.messages:
            return

        for msg in session.messages:
            panel = MessagePanel(
                role=msg.role.value,
                content=msg.content,
                terminal_width=self._terminal_width,
            )
            self.conversation.add_child(panel)

        # Sync token tracker with loaded session messages
        self.alfred.sync_token_tracker_from_session()

        self.tui.request_render(force=True)

    def _add_user_message(self, content: str) -> None:
        """Add a user message panel to the conversation."""
        msg = MessagePanel(role="user", content=content, terminal_width=self._terminal_width)
        self.conversation.add_child(msg)
        self.tui.request_render()

    def _cmd_new_session(self) -> bool:
        """Create a new session."""
        self._clear_conversation()
        session = self.alfred.session_manager.new_session()
        self._add_user_message(f"New session created: {session.meta.session_id}")
        self._update_status()
        return True

    def _cmd_resume_session(self, session_id: str | None) -> bool:
        """Resume an existing session."""
        if not session_id:
            self._add_user_message(
                "Usage: /resume <session_id>\nUse /sessions to see available sessions."
            )
            return True

        try:
            self._clear_conversation()
            self.alfred.session_manager.resume_session(session_id)

            # Load all session messages into conversation
            self._load_session_messages()

            self._update_status()
        except ValueError as e:
            self._add_user_message(f"Error: {e}")
        return True

    def _cmd_list_sessions(self) -> bool:
        """List all sessions."""
        sessions = self.alfred.session_manager.list_sessions()
        if not sessions:
            self._add_user_message("No sessions found.")
            return True

        # Build output using non-breaking spaces to prevent word wrapping
        lines: list[str] = []

        current_id = None
        current_session = None
        if self.alfred.session_manager.has_active_session():
            current_session = self.alfred.session_manager.get_current_cli_session()
            if current_session:
                current_id = current_session.meta.session_id

        for meta in sessions[:20]:
            created = meta.created_at.strftime("%Y-%m-%d %H:%M")
            marker = " (current)" if meta.session_id == current_id else ""
            # Use cached session's message count for current session (more up-to-date)
            msg_count = meta.message_count
            if meta.session_id == current_id and current_session:
                msg_count = current_session.meta.message_count
            # Use non-breaking space (\xa0) between fields to prevent wrapping
            line = f"{meta.session_id}\xa0\xa0{created}\xa0\xa0{msg_count} msgs{marker}"
            lines.append(line)

        if len(sessions) > 20:
            lines.append(f"... and {len(sessions) - 20} more")

        self._add_user_message("\n".join(lines))
        return True

    def _cmd_show_current_session(self) -> bool:
        """Show current session details."""
        if not self.alfred.session_manager.has_active_session():
            self._add_user_message("No active session.")
            return True

        session = self.alfred.session_manager.get_current_cli_session()
        if not session:
            self._add_user_message("No active session.")
            return True

        meta = session.meta
        created = meta.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = meta.last_active.strftime("%Y-%m-%d %H:%M")

        self._add_user_message(
            f"Current Session\n"
            f"ID: {meta.session_id}\n"
            f"Status: {meta.status}\n"
            f"Created: {created}\n"
            f"Last Active: {last_active}\n"
            f"Messages: {meta.message_count}"
        )
        return True

    async def _send_message(self, text: str) -> None:
        """Send message to Alfred and handle response.

        Args:
            text: The user message
        """
        # Mark as streaming (is_sending was already set in _on_submit)
        self._is_streaming = True

        # Create assistant message panel (empty, will stream content)
        assistant_msg = MessagePanel(
            role="assistant", content="", terminal_width=self._terminal_width
        )
        self.conversation.add_child(assistant_msg)
        self._current_assistant_msg = assistant_msg

        first_chunk = True
        next_to_process: str | None = None
        try:
            # Stream response from Alfred
            accumulated = ""
            async for chunk in self.alfred.chat_stream(
                text, tool_callback=self._tool_callback
            ):
                # Clear sending state on first chunk (now actually streaming)
                if first_chunk:
                    self._is_sending = False
                    first_chunk = False
                accumulated += chunk
                assistant_msg.set_content(accumulated)

                # Estimate output tokens during streaming (chars / 4)
                estimated_out = len(accumulated) // 4
                self._update_status(estimated_out=estimated_out)

                self.tui.request_render()

            # Final update with actual token counts
            self._update_status()
        except Exception as e:
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
            if next_to_process.startswith("/") and self._handle_session_command(
                next_to_process
            ):
                return  # Command handled, don't send to LLM

            # Add user message and send to LLM
            user_msg = MessagePanel(
                role="user", content=next_to_process, terminal_width=self._terminal_width
            )
            self.conversation.add_child(user_msg)
            self._update_status()
            asyncio.create_task(self._send_message(next_to_process))

    async def run(self) -> None:
        """Main event loop - reads input, handles events, renders frames."""
        self.tui.start()

        # Load existing session messages on startup
        self._load_session_messages()

        # Update status line with current session state
        self._update_status()

        try:
            while self.running:
                # Track terminal width changes
                new_width = self.terminal.get_size()[0]
                if new_width != self._terminal_width:
                    self._terminal_width = new_width
                    # Update current assistant message if streaming
                    if self._current_assistant_msg:
                        self._current_assistant_msg.set_terminal_width(new_width)

                # Read terminal input with timeout
                data = self.terminal.read_sequence(timeout=0.01)
                if data:
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

                # Update toast overlay visibility
                self._update_toast_overlay()

                # Animate throbber during streaming
                self.status_line.tick_throbber()

                # Render frame
                self.tui.request_render()
                self.tui.render_frame()

                # Yield to event loop (~60fps)
                await asyncio.sleep(0.016)
        finally:
            self.tui.stop()
