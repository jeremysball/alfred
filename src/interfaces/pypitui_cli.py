"""PyPiTUI-based CLI interface for Alfred."""

import asyncio
from contextlib import suppress

from pypitui import TUI, Container, Input, ProcessTerminal, Text

from src.alfred import Alfred


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
        self.status_line = Container()

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

    def _on_submit(self, text: str) -> None:
        """Handle user input submission.

        Args:
            text: The submitted text
        """
        # Strip whitespace and ignore empty
        text = text.strip()
        if not text:
            return

        # Add user message to conversation (simple Text for now)
        user_msg = Text(f"You: {text}")
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

        Placeholder - will be implemented in Phase 1.4
        """
        pass

    async def run(self) -> None:
        """Main event loop - reads input, handles events, renders frames."""
        self.tui.start()
        try:
            while self.running:
                # Read terminal input with timeout
                data = self.terminal.read_sequence(timeout=0.01)
                if data:
                    self.tui.handle_input(data)

                # Render frame
                self.tui.request_render()
                self.tui.render_frame()

                # Yield to event loop (~60fps)
                await asyncio.sleep(0.016)
        finally:
            self.tui.stop()
