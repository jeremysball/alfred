"""Main AlfredTUI class for the CLI interface."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from alfred.alfred import Alfred

# Import commands
from alfred.interfaces.pypitui.commands import (
    Command,
    HealthCommand,
    ListSessionsCommand,
    NewSessionCommand,
    ResumeSessionCommand,
    ShowContextCommand,
    ShowSessionCommand,
    ThrobbersCommand,
)
from alfred.interfaces.pypitui.compat import (
    CompatTUI,
    OverlayHandle,
    OverlayOptions,
    ProcessTerminal,
)
from alfred.interfaces.pypitui.completion_menu_component import CompletionMenuComponent

# Settings now accessed via self.alfred.config
from alfred.interfaces.pypitui.fuzzy import fuzzy_match
from alfred.interfaces.pypitui.history_cache import HistoryManager
from alfred.interfaces.pypitui.key_bindings import BasicKeyHandler, HistoryKeyHandler
from alfred.interfaces.pypitui.message_panel import MessagePanel
from alfred.interfaces.pypitui.status_line import StatusLine
from alfred.interfaces.pypitui.toast import ToastManager
from alfred.interfaces.pypitui.toast_overlay import ToastOverlay
from alfred.interfaces.pypitui.wrapped_input import WrappedInput
from pypitui import Container, Key, matches_key


class AlfredTUI:
    """Main TUI class for Alfred CLI using PyPiTUI."""

    def __init__(
        self,
        alfred: Alfred,
        terminal: "ProcessTerminal | None" = None,
        toast_manager: ToastManager | None = None,
        history_manager: HistoryManager | None = None,
    ) -> None:
        """Initialize the Alfred TUI.

        Args:
            alfred: The Alfred instance to interact with
            terminal: Optional terminal to use (for testing)
            toast_manager: Optional ToastManager for notifications
            history_manager: Optional HistoryManager for testing
                (uses ~/.cache/alfred if not provided)
        """
        self.alfred = alfred
        self.terminal = terminal or ProcessTerminal()
        self.tui = CompatTUI(self.terminal)
        # Resize handling is routed through the compatibility TUI adapter.
        self._toast_manager = toast_manager

        # Initialize terminal width from actual terminal size
        initial_width, _ = self._get_terminal_size(default_width=80, default_height=24)
        self._terminal_width: int = initial_width

        # Main conversation container
        self.conversation = Container()

        # DEBUG
        with open("/tmp/init_debug.log", "a") as f:
            f.write(f"AlfredTUI __init__: conversation id={id(self.conversation)}\n")

        # Status line for model/token info
        self.status_line = StatusLine()

        # Track scrollback position
        self._scrollback_position = 0

        # Completion menu as proper component (renders empty when closed)
        self.completion_menu = CompletionMenuComponent(max_height=10)

        # Input field for user messages (with wrapped text navigation and completion)
        self.input_field = WrappedInput(placeholder="Message Alfred...")
        self.input_field.on_submit = self._on_submit

        # Add hook to reset Ctrl+C state on any keypress
        self.input_field.add_post_input_hook(self._reset_ctrl_c_state)

        # Wire up completion with multiple triggers (longest match wins)
        completion = self.input_field.setup_completion(self.completion_menu)
        completion.register("/", self._command_provider)
        completion.register("/resume ", self._session_id_provider)

        # Build layout: conversation (flex), status, input
        # Completion menu is shown as overlay, not child component
        self.tui.add_child(self.conversation)
        self.tui.add_child(self.status_line)
        self.tui.add_child(self.input_field)
        self.tui.set_focus(self.input_field)

        # DEBUG
        with open("/tmp/init_debug.log", "a") as f:
            f.write(f"TUI children after setup: {len(self.tui.children)}\n")
            for i, child in enumerate(self.tui.children):
                f.write(f"  {i}: {type(child).__name__} id={id(child)}\n")
                if hasattr(child, 'children'):
                    f.write(f"      has {len(child.children)} children\n")

        # Toast overlay (non-modal popup at bottom of screen)
        self._toast_overlay: ToastOverlay | None = None
        self._toast_handle: OverlayHandle | None = None
        if toast_manager is not None:
            self._toast_overlay = ToastOverlay(toast_manager)

        # Completion menu overlay handle
        self._completion_handle: OverlayHandle | None = None

        # State
        self.running = True

        # Ctrl-C state
        self._ctrl_c_pending = False

        # History manager for per-directory message history
        if history_manager is not None:
            self._history_manager = history_manager
        else:
            cache_dir = Path.home() / ".cache" / "alfred"
            work_dir = Path.cwd()
            self._history_manager = HistoryManager(work_dir, cache_dir)

        # Key handlers for history and shortcuts
        self._history_handler = HistoryKeyHandler(self._history_manager, self.input_field)
        self._basic_handler = BasicKeyHandler(self.input_field)

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
            "/throbbers": ThrobbersCommand(),
            "/health": HealthCommand(),
        }

        # Toast manager is passed directly, no need to configure through notifier
        # Socket-based cron runner sends notifications via Unix socket

        # Add input listener for queue navigation (ESC to cancel, UP/DOWN for history)
        self.tui.add_input_listener(self._input_listener)

        # Initialize status line with current values
        self._update_status()

    def _get_terminal_size(
        self, default_width: int = 80, default_height: int = 24
    ) -> tuple[int, int]:
        """Safely read the terminal size from any terminal-like object."""
        getter = getattr(self.terminal, "get_size", None)
        if callable(getter):
            try:
                width, height = getter()
                return (int(width), int(height))
            except Exception:
                pass
        return (default_width, default_height)

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
            # Request render to show cleared input and toast
            self.tui.request_render()

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

    def _update_completion_overlay(self) -> None:
        """Update completion menu overlay visibility.

        Shows overlay when menu is open, hides when closed.
        Menu is positioned above the input field.
        """
        menu_open = self.completion_menu.is_open

        if menu_open and self._completion_handle is None:
            # Show completion menu as overlay above input field
            # Position: just above the input line(s)
            input_lines = len(self.input_field.render(self._terminal_width))
            # Offset up by input lines to appear directly above input
            offset_y = -input_lines

            options = OverlayOptions(
                anchor="bottom-left",
                offset_y=offset_y,
                margin=0,
            )
            self._completion_handle = self.tui.show_overlay(self.completion_menu, options)
        elif not menu_open and self._completion_handle is not None:
            # Hide completion menu
            self._completion_handle.hide()
            self._completion_handle = None

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
                getattr(child, "set_terminal_width")(term_width)  # noqa: B009

        # Re-populate scrollback if there's overflow content
        self._populate_scrollback_by_scrolling()

    def _calculate_static_height(self) -> int:
        """Calculate total height of fixed (non-scrollable) UI components.

        Walks from bottom to top, summing heights of static components.
        This includes: status_line, completion_menu (if open), input_field.

        Returns:
            Total height in terminal rows occupied by fixed components.
        """
        # Always use actual terminal width for accurate calculations
        # Using cached self._terminal_width causes layout issues after resize
        term_width, _ = self._get_terminal_size(default_width=self._terminal_width)
        static_height = 0

        # Input field (always visible at bottom)
        # WrappedInput renders at least 1 line, more if text wraps
        input_lines = len(self.input_field.render(term_width))
        static_height += input_lines

        # Status line (always visible, above input)
        status_lines = len(self.status_line.render(term_width))
        static_height += status_lines

        # Note: Completion menu is now an overlay, not included in static height

        return static_height

    def _handle_control_keys(self, data: str) -> dict[str, Any] | None:
        """Handle control key shortcuts.

        Args:
            data: The input data to process.

        Returns:
            {"consume": True} if key was handled, None otherwise.
        """
        # Ctrl+U: Clear from cursor to start of line
        if data == "\x15" and self._basic_handler.on_clear_line():  # Ctrl+U
            return {"consume": True}

        # Ctrl+A: Move to start of line
        if data == "\x01" and self._basic_handler.on_start_of_line():  # Ctrl+A
            return {"consume": True}

        # Ctrl+E: Move to end of line
        if data == "\x05" and self._basic_handler.on_end_of_line():  # Ctrl+E
            return {"consume": True}

        # Ctrl+L: Clear screen
        if data == "\x0c":  # Ctrl+L
            self.terminal.write("\x1b[2J\x1b[H")
            return {"consume": True}

        # Ctrl+6 or Ctrl+^: Vim-style start of line
        if data == "\x1e" and self._basic_handler.on_vim_start_of_line():  # Ctrl+6/^
            return {"consume": True}

        # Ctrl+4 or Ctrl+$: Vim-style end of line
        if data == "\x1c" and self._basic_handler.on_vim_end_of_line():  # Ctrl+4/$
            return {"consume": True}

        # Ctrl+Left: Move word left
        if data == "\x1b[1;5D" and self._basic_handler.on_word_left():
            return {"consume": True}

        # Ctrl+Right: Move word right
        if data == "\x1b[1;5C" and self._basic_handler.on_word_right():
            return {"consume": True}

        return None

    def _handle_escape_key(self) -> dict[str, Any] | None:
        """Handle escape key - clears message queue if not empty.

        Returns:
            {"consume": True} if queue was cleared, None otherwise.
        """
        if self._message_queue:
            self._message_queue.clear()
            self._queue_nav_index = -1
            self._queue_draft = ""
            self.input_field.set_value("")
            self._update_status()
            return {"consume": True}
        return None

    def _handle_up_navigation(self, cursor_line: int) -> dict[str, Any] | None:
        """Handle UP arrow key - queue nav first, then history.

        Args:
            cursor_line: The current cursor line (0-indexed).

        Returns:
            {"consume": True} if handled, None otherwise.
        """
        if cursor_line != 0:
            return None

        # First try message queue navigation
        if self._message_queue:
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

        # Fall back to history navigation
        if self._history_handler.on_history_up():
            return {"consume": True}

        return None

    def _handle_down_navigation(self) -> dict[str, Any] | None:
        """Handle DOWN arrow key - queue nav first, then history.

        Returns:
            {"consume": True} if handled, None otherwise.
        """
        # First try message queue navigation
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

        # Fall back to history navigation
        if self._history_handler.on_history_down():
            return {"consume": True}

        return None

    def _reset_queue_navigation(self) -> None:
        """Reset queue navigation state when other keys are pressed."""
        self._queue_nav_index = -1
        self._queue_draft = ""

    def _input_listener(self, data: str) -> dict[str, Any] | None:
        """Intercept input for history navigation, shortcuts, and queue management.

        Returns:
            {"consume": True} to block input from reaching input field,
            None to allow input to pass through.
        """
        # Handle control keys
        if result := self._handle_control_keys(data):
            return result

        # Handle escape key
        if matches_key(data, Key.escape):
            return self._handle_escape_key()

        # Handle UP arrow
        if matches_key(data, Key.up):
            cursor_line = self._get_input_cursor_line()
            return self._handle_up_navigation(cursor_line)

        # Handle DOWN arrow
        if matches_key(data, Key.down):
            return self._handle_down_navigation()

        # Any other key resets queue navigation
        if self._queue_nav_index != -1:
            self._reset_queue_navigation()

        return None

    def _get_input_cursor_line(self) -> int:
        """Get which display line the cursor is on (0-indexed)."""
        width = self._get_terminal_size(default_width=self._terminal_width)[0]
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
        from alfred.agent import ToolEnd, ToolOutput, ToolStart

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

        # DEBUG: Verify the message was added
        with open("/tmp/alfred_debug.log", "a") as f:
            f.write(f"Added message: {repr(text)}\n")
            f.write(f"  conversation id: {id(self.conversation)}\n")
            f.write(f"  conversation children: {len(self.conversation.children)}\n")
            f.write(f"  child type: {type(self.conversation.children[0]).__name__}\n")
            lines = self.conversation.children[0].render(80)
            f.write(f"  rendered lines: {len(lines)}\n")
            for i, line in enumerate(lines):
                f.write(f"    line {i}: {line[:50]}\n")

        # Add to history for future recall
        self._history_manager.add(text)

        # Start sending state immediately for throbber feedback
        self._is_sending = True
        self._update_status()

        # Create async task for response (requires running event loop)
        coro = self._send_message(text)
        try:
            asyncio.create_task(coro)
        except RuntimeError:
            coro.close()

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
            ("/throbbers", "Show throbber animations"),
            ("/health", "Show system health status"),
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

        # Get available sessions with metadata (uses sync list_sessions)
        sessions = self.alfred.core.session_manager.list_sessions()
        sessions_with_meta: list[tuple[str, str | None, datetime]] = []

        for session in sessions:
            sid = session.session_id
            # Fuzzy match against partial ID
            if not fuzzy_match(partial.lower(), sid.lower()):
                continue

            # Format: "Mar 3 21:45 · 12 msgs"
            date_str = session.last_active.strftime("%b %-d %H:%M")
            msg_count = session.message_count
            desc = f"{date_str} · {msg_count} msgs"
            sessions_with_meta.append((sid, desc, session.last_active))

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
        self.terminal.write("\x1b[2J\x1b[H")
        if hasattr(self.tui, "reset_scrollback_state"):
            getattr(self.tui, "reset_scrollback_state")()  # noqa: B009

    async def _load_session_messages(self) -> None:
        """Load existing session messages into conversation panel.

        Called on startup (if resuming) and after /resume command.
        Renders all historical messages as MessagePanels.

        Sets scrollback position so older messages flow into terminal
        scrollback history instead of all being rendered on screen.
        """
        if not self.alfred.core.session_manager.has_active_session():
            return

        session = await self.alfred.core.session_manager.get_current_cli_session_async()
        if not session or not session.messages:
            return

        # Add all message panels to conversation
        for msg in session.messages:
            panel = MessagePanel(
                role=msg.role.value,
                content=msg.content,
                terminal_width=self._terminal_width,
                use_markdown=self.alfred.config.use_markdown_rendering,
            )
            # Restore tool calls for assistant messages
            if msg.role.value == "assistant" and msg.tool_calls:
                panel.restore_tool_calls_from_records(msg.tool_calls)
            self.conversation.add_child(panel)

        # Sync token tracker with loaded session messages
        self.alfred.sync_token_tracker_from_session()

        # Populate scrollback: render screenfuls and scroll them into history
        self._populate_scrollback_by_scrolling()

        self.tui.request_render()

    def _populate_scrollback_by_scrolling(self) -> None:
        """Populate terminal scrollback by rendering and scrolling content.

        DEPRECATED: This method is no longer needed. PyPiTUI now handles
        scrollback naturally through _handle_content_growth. DECSTBM scroll
        regions interfere with the new transient component rendering.

        Kept for backwards compatibility but does nothing.
        """
        # Scrollback is now handled automatically by pypitui's
        # _handle_content_growth method. Lines flow into scrollback
        # naturally as content grows beyond terminal height.
        pass

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
        """Main event loop - process input and render every frame."""
        # Set up signal handlers
        import signal

        def _handle_sigwinch(_signum: int, _frame: object) -> None:
            """Handle terminal resize signal."""
            term_width, term_height = self._get_terminal_size(
                default_width=self._terminal_width
            )
            self._on_resize(term_width, term_height)
            self.tui.request_resize_check()
            self.tui.request_render(force=True)

        def _handle_sigint(_signum: int, _frame: object) -> None:
            """Handle SIGINT (Ctrl+C) gracefully even if terminal not in raw mode."""
            self._handle_ctrl_c()

        # Install our custom handlers
        old_sigwinch_handler = signal.signal(signal.SIGWINCH, _handle_sigwinch)
        old_sigint_handler = signal.signal(signal.SIGINT, _handle_sigint)

        self.tui.start()
        await self._load_session_messages()
        self._update_status()

        try:
            while self.running:
                # Check for input
                data = self.terminal.read_sequence(timeout=0.0)

                # Check for Ctrl+C (handled as raw input when terminal in raw mode)
                if data == "\x03":  # Ctrl+C
                    self._handle_ctrl_c()
                    if not self.running:
                        break
                    continue

                # Handle other input
                if data:
                    self.tui.handle_input(data)

                # Throbber animation (marks render needed on change)
                if self.status_line.tick_throbber():
                    self.tui.request_render()

                # Update toast overlay visibility
                self._update_toast_overlay()

                # Manage completion menu overlay visibility
                self._update_completion_overlay()

                # Render every frame - diff renderer only outputs changes
                self.tui.render_frame()

                await asyncio.sleep(0.016)
        finally:
            self.tui.stop()
            # Restore original signal handlers
            signal.signal(signal.SIGWINCH, old_sigwinch_handler)
            signal.signal(signal.SIGINT, old_sigint_handler)
            await self.alfred.stop()
