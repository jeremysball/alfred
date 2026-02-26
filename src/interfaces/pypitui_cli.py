"""PyPiTUI-based CLI interface for Alfred."""

import asyncio
from contextlib import suppress
from typing import Literal

from pypitui import (  # type: ignore
    TUI,
    BorderedBox,
    Component,
    Container,
    Input,
    Key,
    ProcessTerminal,
    Text,
    matches_key,
)

from src.alfred import Alfred

# ANSI color codes for borders
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
RESET = "\x1b[0m"
DIM = "\x1b[2m"


def format_tokens(n: int) -> str:
    """Format token count: 1234567 -> 1.2M, 12345 -> 12K, 123 -> 123."""
    if n >= 1_000_000:
        value = n / 1_000_000
        if value == int(value):
            return f"{int(value)}M"
        return f"{value:.1f}M"
    elif n >= 1_000:
        value = n / 1_000
        if value == int(value):
            return f"{int(value)}K"
        return f"{value:.1f}K"
    return str(n)


class MessagePanel(BorderedBox):  # type: ignore[misc]
    """A bordered panel for displaying conversation messages.

    Uses different border colors based on role:
    - user: cyan border, title "You"
    - assistant: green border, title "Alfred"
    - error: red border (after set_error() called)
    """

    def __init__(
        self,
        role: Literal["user", "assistant"],
        content: str = "",
        *,
        padding_x: int = 1,
        padding_y: int = 0,
    ) -> None:
        """Initialize the message panel.

        Args:
            role: "user" or "assistant"
            content: Initial message content
            padding_x: Horizontal padding inside border
            padding_y: Vertical padding inside border
        """
        super().__init__(padding_x=padding_x, padding_y=padding_y)

        self._role = role
        self._content = content
        self._is_error = False
        self._border_color = GREEN

        # Set title based on role
        title = "You" if role == "user" else "Alfred"
        self.set_title(title)

        # Set border color based on role
        self._set_border_color(role)

        # Add content as Text child
        if content:
            self.add_child(Text(content))

    def _set_border_color(self, role_or_state: str) -> None:
        """Set border color by overriding class border characters.

        Args:
            role_or_state: "user", "assistant", or "error"
        """
        color = {"user": CYAN, "assistant": GREEN, "error": RED}.get(
            role_or_state, GREEN
        )
        self._border_color = color
        # Override border characters with colored versions
        self.TOP_LEFT = f"{color}┌{RESET}"
        self.TOP_RIGHT = f"{color}┐{RESET}"
        self.BOTTOM_LEFT = f"{color}└{RESET}"
        self.BOTTOM_RIGHT = f"{color}┘{RESET}"
        self.HORIZONTAL = f"{color}─{RESET}"
        self.VERTICAL = f"{color}│{RESET}"
        self.T_LEFT = f"{color}├{RESET}"
        self.T_RIGHT = f"{color}┤{RESET}"
        self._invalidate_cache()

    def set_content(self, text: str) -> None:
        """Update the message content.

        Args:
            text: New content text
        """
        self._content = text
        # Clear existing children and add new Text
        self.clear()
        self.add_child(Text(text))
        self.invalidate()

    def set_error(self, error_msg: str) -> None:
        """Set panel to error state with red border.

        Args:
            error_msg: Error message to display
        """
        self._is_error = True
        self._set_border_color("error")
        self.set_content(f"Error: {error_msg}")


class StatusLine(Component):
    """Status line showing model name and token usage.

    Format: model | ctx N in N out N | cached N reasoning N

    - ctx: context tokens (hidden if 0)
    - in/out: cumulative session tokens (always shown)
    - cached/reasoning: optional (hidden if 0)
    """

    def __init__(self) -> None:
        """Initialize status line with empty state."""
        super().__init__()
        self._model: str = ""
        self._ctx: int = 0
        self._in: int = 0
        self._out: int = 0
        self._cached: int = 0
        self._reasoning: int = 0
        self._exit_hint: bool = False

    def invalidate(self) -> None:
        """Mark this component as needing re-render."""
        # StatusLine is simple - no cached state to invalidate
        pass

    def update(
        self,
        model: str,
        ctx: int,
        in_tokens: int,
        out_tokens: int,
        cached: int,
        reasoning: int,
        exit_hint: bool = False,
    ) -> None:
        """Update all status values.

        Args:
            model: Model name (e.g., "kimi/moonshot-v1")
            ctx: Context window tokens
            in_tokens: Cumulative input tokens
            out_tokens: Cumulative output tokens
            cached: Cache read tokens
            reasoning: Reasoning tokens
            exit_hint: Show Ctrl-C exit hint
        """
        self._model = model
        self._ctx = ctx
        self._in = in_tokens
        self._out = out_tokens
        self._cached = cached
        self._reasoning = reasoning
        self._exit_hint = exit_hint

    def render(self, width: int) -> list[str]:
        """Render status line.

        Args:
            width: Terminal width

        Returns:
            Single-element list with status line string
        """
        parts: list[str] = []

        # Group 1: model name
        parts.append(self._model)

        # Group 2: tokens (always show in/out)
        token_parts: list[str] = []
        if self._ctx > 0:
            token_parts.append(f"ctx {format_tokens(self._ctx)}")
        token_parts.append(f"in {format_tokens(self._in)}")
        token_parts.append(f"out {format_tokens(self._out)}")
        parts.append(" ".join(token_parts))

        # Group 3: cached/reasoning (only if non-zero)
        cache_parts: list[str] = []
        if self._cached > 0:
            cache_parts.append(f"cached {format_tokens(self._cached)}")
        if self._reasoning > 0:
            cache_parts.append(f"reasoning {format_tokens(self._reasoning)}")
        if cache_parts:
            parts.append(" ".join(cache_parts))

        # Exit hint
        if self._exit_hint:
            parts.append(f"{DIM}Press Ctrl-C again to exit{RESET}")

        return [" | ".join(parts)]


class AlfredTUI:
    """Main TUI class for Alfred CLI using PyPiTUI."""

    def __init__(self, alfred: Alfred, terminal: ProcessTerminal | None = None) -> None:
        """Initialize the Alfred TUI.

        Args:
            alfred: The Alfred instance to interact with
            terminal: Optional terminal to use (for testing)
        """
        self.alfred = alfred
        self.terminal = terminal or ProcessTerminal()
        self.tui = TUI(self.terminal)

        # Main conversation container
        self.conversation = Container()

        # Status line for model/token info
        self.status_line = StatusLine()

        # Input field for user messages
        self.input_field = Input(placeholder="Message Alfred...")
        self.input_field.on_submit = self._on_submit

        # Build layout: conversation (flex), status, input
        self.tui.add_child(self.conversation)
        self.tui.add_child(self.status_line)
        self.tui.add_child(self.input_field)
        self.tui.set_focus(self.input_field)

        # State
        self.running = True

        # Ctrl-C state (Phase 1.9)
        self._ctrl_c_pending = False
        self._exit_hint_visible = False

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
        """Reset Ctrl-C pending state (called on any other key)."""
        self._ctrl_c_pending = False
        self._exit_hint_visible = False
        self._update_status()

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
        )

    def _on_submit(self, text: str) -> None:
        """Handle user input submission.

        Args:
            text: The submitted text
        """
        # Strip whitespace and ignore empty
        text = text.strip()
        if not text:
            return

        # Add user message to conversation using MessagePanel
        user_msg = MessagePanel(role="user", content=text)
        self.conversation.add_child(user_msg)

        # Clear input field
        self.input_field.set_value("")

        # Create async task for response (requires running event loop)
        # In production, run() provides the event loop
        with suppress(RuntimeError):
            asyncio.create_task(self._send_message(text))

    async def _send_message(self, text: str) -> None:
        """Send message to Alfred and handle response.

        Args:
            text: The user message
        """
        # Create assistant message panel (empty, will stream content)
        assistant_msg = MessagePanel(role="assistant", content="")
        self.conversation.add_child(assistant_msg)

        try:
            # Stream response from Alfred
            accumulated = ""
            async for chunk in self.alfred.chat_stream(text):
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

                # Render frame
                self.tui.request_render()
                self.tui.render_frame()

                # Yield to event loop (~60fps)
                await asyncio.sleep(0.016)
        finally:
            self.tui.stop()
