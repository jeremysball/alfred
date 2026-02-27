"""MessagePanel component for displaying conversation messages."""

from typing import Literal

from pypitui import BorderedBox, Text  # type: ignore

from src.interfaces.pypitui.constants import CYAN, GREEN, RED, RESET
from src.interfaces.pypitui.models import ToolCallInfo


class MessagePanel(BorderedBox):  # type: ignore[misc]
    """A bordered panel for displaying conversation messages.

    Uses different border colors based on role:
    - user: cyan border, title "You"
    - assistant: green border, title "Alfred"
    - error: red border (after set_error() called)

    Supports embedded tool call boxes for inline tool display.
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
        self._text_content = content
        self._is_error = False
        self._border_color = GREEN

        # Tool calls embedded in this message
        self._tool_calls: list[ToolCallInfo] = []

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
        self._text_content = text
        self._rebuild_content()

    def set_error(self, error_msg: str) -> None:
        """Set panel to error state with red border.

        Args:
            error_msg: Error message to display
        """
        self._is_error = True
        self._set_border_color("error")
        self.set_content(f"Error: {error_msg}")

    # --- Tool Call Methods ---

    def add_tool_call(self, tool_name: str, tool_call_id: str) -> None:
        """Add an embedded tool call box at current text position.

        Args:
            tool_name: Name of the tool
            tool_call_id: Unique ID for this tool call
        """
        tool_info = ToolCallInfo(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            insert_position=len(self._text_content),
        )
        self._tool_calls.append(tool_info)
        self._rebuild_content()

    def update_tool_call(self, tool_call_id: str, output: str) -> None:
        """Update output for a tool call.

        Args:
            tool_call_id: ID of the tool call to update
            output: New output text to append
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.output = output
                self._rebuild_content()
                return

    def finalize_tool_call(
        self, tool_call_id: str, status: Literal["success", "error"]
    ) -> None:
        """Set final status for a tool call.

        Args:
            tool_call_id: ID of the tool call to finalize
            status: Final status (success or error)
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.status = status
                self._rebuild_content()
                return

    def get_tool_call(self, tool_call_id: str) -> ToolCallInfo | None:
        """Get a tool call by ID.

        Args:
            tool_call_id: ID of the tool call

        Returns:
            ToolCallInfo if found, None otherwise
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                return tc
        return None

    def _rebuild_content(self) -> None:
        """Rebuild the content with embedded tool call boxes."""
        self.clear()

        if not self._tool_calls:
            # Simple case: no tool calls
            self.add_child(Text(self._text_content))
        else:
            # Build content with tool boxes inline
            self._build_content_with_tools()

        self.invalidate()

    def _build_content_with_tools(self) -> None:
        """Build content string with tool call boxes embedded."""
        from src.interfaces.pypitui.constants import DIM_BLUE, DIM_GREEN, DIM_RED

        # Build the full content with tool boxes as inline text
        # This is a simplified approach - renders tool info as indented text
        parts: list[str] = []

        # Sort tool calls by position
        sorted_tools = sorted(self._tool_calls, key=lambda t: t.insert_position)

        last_pos = 0
        for tc in sorted_tools:
            # Add text before this tool
            if last_pos < tc.insert_position:
                parts.append(self._text_content[last_pos : tc.insert_position])

            # Add tool box (simplified as indented text with status color)
            color = {"running": DIM_BLUE, "success": DIM_GREEN, "error": DIM_RED}.get(
                tc.status, DIM_BLUE
            )
            tool_box = f"\n{color}  ┌─ {tc.tool_name} ─{'─' * 20}{RESET}\n"
            if tc.output:
                # Truncate output for display
                display_output = tc.output[-200:] if len(tc.output) > 200 else tc.output
                for line in display_output.split("\n"):
                    tool_box += f"{color}  │{RESET} {line}\n"
            tool_box += f"{color}  └{'─' * 30}{RESET}\n"
            parts.append(tool_box)

            last_pos = tc.insert_position

        # Add remaining text after last tool
        if last_pos < len(self._text_content):
            parts.append(self._text_content[last_pos:])

        content = "".join(parts)
        self.add_child(Text(content))

    @property
    def tool_calls(self) -> list[ToolCallInfo]:
        """Get list of tool calls in this message."""
        return self._tool_calls

    @property
    def _content(self) -> str:
        """Get the text content (backwards compat)."""
        return self._text_content
