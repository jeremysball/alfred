"""ToolCallPanel component for displaying tool execution."""

from typing import Literal

from pypitui import BorderedBox, Text  # type: ignore

from src.interfaces.pypitui.constants import (
    DIM_BLUE,
    DIM_GREEN,
    DIM_RED,
    MAX_TOOL_OUTPUT,
    RESET,
)


class ToolCallPanel(BorderedBox):  # type: ignore[misc]
    """A dimmed panel for displaying tool execution.

    Uses dim border colors (less prominent than messages):
    - running: dim blue border
    - success: dim green border
    - error: dim red border

    Output is truncated to ~500 chars, keeping the end.
    """

    def __init__(
        self,
        tool_name: str,
        tool_call_id: str,
        *,
        padding_x: int = 1,
        padding_y: int = 0,
    ) -> None:
        """Initialize the tool call panel.

        Args:
            tool_name: Name of the tool (e.g., "remember", "bash")
            tool_call_id: Unique ID for this tool call
            padding_x: Horizontal padding inside border
            padding_y: Vertical padding inside border
        """
        super().__init__(padding_x=padding_x, padding_y=padding_y)

        self._tool_name = tool_name
        self._tool_call_id = tool_call_id
        self._output = ""
        self._status: Literal["running", "success", "error"] = "running"

        # Set title to tool name
        self.set_title(tool_name)

        # Start with dim blue border (running)
        self._set_border_color("running")

    def _set_border_color(self, status: Literal["running", "success", "error"]) -> None:
        """Set border color based on status.

        Args:
            status: "running", "success", or "error"
        """
        color = {"running": DIM_BLUE, "success": DIM_GREEN, "error": DIM_RED}.get(
            status, DIM_BLUE
        )
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

    def append_output(self, chunk: str) -> None:
        """Append output chunk, truncating if needed.

        Keeps the END of output when truncating.

        Args:
            chunk: Output chunk to append
        """
        self._output += chunk
        # Truncate to MAX_TOOL_OUTPUT chars, keeping end
        if len(self._output) > MAX_TOOL_OUTPUT:
            self._output = self._output[-MAX_TOOL_OUTPUT:]

        # Update display
        self.clear()
        self.add_child(Text(self._output))
        self.invalidate()

    def set_status(self, status: Literal["running", "success", "error"]) -> None:
        """Set the tool execution status.

        Args:
            status: "running", "success", or "error"
        """
        self._status = status
        self._set_border_color(status)

    @property
    def tool_name(self) -> str:
        """Get the tool name."""
        return self._tool_name

    @property
    def tool_call_id(self) -> str:
        """Get the tool call ID."""
        return self._tool_call_id

    @property
    def output(self) -> str:
        """Get the accumulated output."""
        return self._output

    @property
    def status(self) -> Literal["running", "success", "error"]:
        """Get the current status."""
        return self._status
