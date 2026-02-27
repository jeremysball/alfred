"""Main AlfredTUI class for the CLI interface."""

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Literal

from pypitui import Container, Key, OverlayOptions, matches_key

from src.alfred import Alfred
from src.interfaces.pypitui.message_panel import MessagePanel
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
        from pypitui import TUI, ProcessTerminal

        self.alfred = alfred
        self.terminal = terminal or ProcessTerminal()
        self.tui = TUI(self.terminal)
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

        # Ctrl-C state
        self._ctrl_c_pending = False
        self._exit_hint_visible = False

        # Current assistant message for inline tool calls
        self._current_assistant_msg: MessagePanel | None = None

        # Input queue for messages during streaming
        self._message_queue: list[str] = []
        self._is_streaming = False
        self._is_sending = False  # True while waiting for first chunk

        # Enable toast mode for cron job notifications
        if toast_manager is not None:
            from src.cron.notifier import CLINotifier

            if isinstance(self.alfred.notifier, CLINotifier):
                self.alfred.notifier.set_toast_manager(toast_manager)

    def _handle_ctrl_c(self) -> None:
        """Handle Ctrl-C keypress.

        First Ctrl-C: clear input, show hint.
        Second Ctrl-C: exit.
        """
        if self._ctrl_c_pending:
            # Second Ctrl-C - exit
            self.running = False
        else:
            # First Ctrl-C - clear input and show hint
            self.input_field.set_value("")
            self._ctrl_c_pending = True
            self._exit_hint_visible = True
            self._update_status()

    def _reset_ctrl_c_state(self) -> None:
        """Reset Ctrl-C pending state and dismiss toasts (called on any other key)."""
        self._ctrl_c_pending = False
        self._exit_hint_visible = False
        self._update_status()
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
            exit_hint=self._exit_hint_visible,
            queued=len(self._message_queue),
            streaming=self._is_streaming or self._is_sending,
        )

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

        # Add user message to conversation
        user_msg = MessagePanel(role="user", content=text)
        self.conversation.add_child(user_msg)

        # Clear input field
        self.input_field.set_value("")

        # Start sending state immediately for throbber feedback
        self._is_sending = True
        self._update_status()

        # Create async task for response (requires running event loop)
        with suppress(RuntimeError):
            asyncio.create_task(self._send_message(text))

    async def _send_message(self, text: str) -> None:
        """Send message to Alfred and handle response.

        Args:
            text: The user message
        """
        # Mark as streaming (is_sending was already set in _on_submit)
        self._is_streaming = True

        # Create assistant message panel (empty, will stream content)
        assistant_msg = MessagePanel(role="assistant", content="")
        self.conversation.add_child(assistant_msg)
        self._current_assistant_msg = assistant_msg

        first_chunk = True
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

            # Process queued messages
            if self._message_queue:
                next_text = self._message_queue.pop(0)
                # Add user message and send
                user_msg = MessagePanel(role="user", content=next_text)
                self.conversation.add_child(user_msg)
                self._update_status()
                asyncio.create_task(self._send_message(next_text))

    async def run(self) -> None:
        """Main event loop - reads input, handles events, renders frames."""
        self.tui.start()
        try:
            while self.running:
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
