"""Message panel component for displaying conversation messages with tool calls."""

from __future__ import annotations

import re
from typing import Literal

from alfred.interfaces.ansi import (
    BOLD,
    BRIGHT_GREEN,
    BRIGHT_RED,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
)
from alfred.interfaces.pypitui.box_utils import build_bordered_box
from alfred.interfaces.pypitui.models import ToolCallInfo
from alfred.interfaces.pypitui.rich_renderer import RichRenderer
from pypitui import Component
from pypitui.component import Size


class MessagePanel(Component):
    """Panel for displaying a message with optional tool calls."""

    # Width thresholds for responsive display
    NARROW_WIDTH = 60  # ≤60: minimal display
    MEDIUM_WIDTH = 100  # 61-100: moderate detail
    # >100: full detail

    def __init__(
        self,
        role: Literal["user", "assistant"],
        content: str,
        terminal_width: int = 80,
        use_markdown: bool = True,
    ) -> None:
        """Initialize message panel.

        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            terminal_width: Terminal width for responsive rendering
            use_markdown: Whether to render markdown
        """
        self._role = role
        self._text_content = content
        self._terminal_width = terminal_width
        self._use_markdown = use_markdown
        self._error: str | None = None
        self._tool_calls: list[ToolCallInfo] = []
        self._tool_call_sequence = 0
        self._expanded = False
        self.children: list[Component] = []  # For compatibility with tests

        # Border colors based on role
        if role == "user":
            self._border_color = CYAN
            self._title = "You"
        else:
            self._border_color = GREEN
            self._title = "Alfred"

        # Initialize renderer with content area width
        content_width = max(terminal_width - 8, RichRenderer.MIN_WIDTH)
        self._renderer = RichRenderer(width=content_width) if use_markdown else None

    def set_terminal_width(self, width: int) -> None:
        """Update terminal width for responsive rendering.

        Args:
            width: New terminal width
        """
        self._terminal_width = width
        if self._renderer:
            content_width = max(width - 8, RichRenderer.MIN_WIDTH)
            self._renderer.update_width(content_width)

    def set_content(self, content: str) -> None:
        """Update message content.

        Args:
            content: New content
        """
        self._text_content = content

    def set_error(self, error: str) -> None:
        """Set error state.

        Args:
            error: Error message
        """
        self._error = error
        self._border_color = RED

    def set_expanded(self, expanded: bool) -> None:
        """Set expanded state for tool calls.

        Args:
            expanded: Whether to show full tool output
        """
        self._expanded = expanded

    def add_tool_call(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict[str, object] | None = None,
    ) -> None:
        """Add a tool call to this message.

        Args:
            tool_name: Name of the tool
            tool_call_id: Unique ID for the tool call
            arguments: Tool arguments
        """
        # Get current insert position based on text content length
        insert_position = len(self._text_content)

        tool_call = ToolCallInfo(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            arguments=arguments or {},
            insert_position=insert_position,
            sequence=self._tool_call_sequence,
        )
        self._tool_calls.append(tool_call)
        self._tool_call_sequence += 1

        # Add a placeholder child component for test compatibility
        from pypitui.components.text import Text

        self.children.append(Text(f"tool:{tool_name}"))

    def update_tool_call(self, tool_call_id: str, output: str) -> None:
        """Update tool call output.

        Args:
            tool_call_id: ID of the tool call to update
            output: New output content
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.output = output
                break

    def finalize_tool_call(self, tool_call_id: str, status: Literal["success", "error"]) -> None:
        """Finalize a tool call with its status.

        Args:
            tool_call_id: ID of the tool call to finalize
            status: Final status ("success" or "error")
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.status = status
                break

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

    def _format_tool_arguments(self, tool_name: str, arguments: dict[str, object]) -> str:
        """Format tool arguments for display based on terminal width.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments dict

        Returns:
            Formatted arguments string
        """
        if not arguments:
            return ""

        # Special handling for write command - don't show raw JSON
        if tool_name == "write":
            return self._format_write_arguments(arguments)

        # Format arguments as key=value pairs
        args_list = []
        for key, value in arguments.items():
            if isinstance(value, str):
                # Truncate long strings
                if len(value) > 50:
                    value = value[:47] + "..."
                args_list.append(f"{key}={value}")
            elif isinstance(value, (list, dict)):
                # Show type info for complex objects
                args_list.append(f"{key}=[{type(value).__name__}]")
            else:
                args_list.append(f"{key}={value}")

        return ", ".join(args_list)

    def _format_write_arguments(self, arguments: dict[str, object]) -> str:
        """Format write tool arguments nicely.

        Args:
            arguments: Write tool arguments

        Returns:
            Formatted string showing path and content preview
        """
        path = arguments.get("path", "")
        content = arguments.get("content", "")

        if not path:
            return ""

        # Calculate available space based on terminal width
        if self._terminal_width <= self.NARROW_WIDTH:
            # Narrow: just show filename
            filename = path.split("/")[-1] if "/" in path else path
            return f"→ {filename}"
        elif self._terminal_width <= self.MEDIUM_WIDTH:
            # Medium: show path (truncated if needed)
            max_path = self._terminal_width - 20
            display_path = path if len(path) <= max_path else "..." + path[-(max_path - 3) :]
            return f"→ {display_path}"
        else:
            # Wide: show path and content preview
            max_path = 40
            display_path = path if len(path) <= max_path else "..." + path[-(max_path - 3) :]

            # Add content preview
            if content and isinstance(content, str):
                preview = content.replace("\n", " ")[:50]
                if len(content) > 50:
                    preview += "..."
                return f"→ {display_path}: {preview}"

            return f"→ {display_path}"

    def _get_tool_display_info(self, tool_call: ToolCallInfo) -> tuple[str, str]:
        """Get display title and subtitle for a tool call based on terminal width.

        Args:
            tool_call: The tool call to format

        Returns:
            Tuple of (title, subtitle/info line)
        """
        tool_name = tool_call.tool_name
        arguments = tool_call.arguments

        # Determine status indicator
        if tool_call.status == "running":
            status_indicator = f"{YELLOW}●{RESET}"
        elif tool_call.status == "success":
            status_indicator = f"{BRIGHT_GREEN}✓{RESET}"
        else:
            status_indicator = f"{BRIGHT_RED}✗{RESET}"

        # Build title based on width
        if self._terminal_width <= self.NARROW_WIDTH:
            # Narrow: just tool name and status
            title = f"{status_indicator} {BOLD}{tool_name}{RESET}"
            subtitle = ""
        elif self._terminal_width <= self.MEDIUM_WIDTH:
            # Medium: tool name + key arguments
            args_str = self._format_tool_arguments(tool_name, arguments)
            if args_str:
                # Truncate args to fit
                max_args = self._terminal_width - 30
                if len(args_str) > max_args:
                    args_str = args_str[: max_args - 3] + "..."
                title = f"{status_indicator} {BOLD}{tool_name}{RESET}"
                subtitle = args_str
            else:
                title = f"{status_indicator} {BOLD}{tool_name}{RESET}"
                subtitle = ""
        else:
            # Wide: full details
            args_str = self._format_tool_arguments(tool_name, arguments)
            title = f"{status_indicator} {BOLD}{tool_name}{RESET}"

            # For bash, show the full command prominently
            if tool_name == "bash" and arguments:
                command = arguments.get("command", "")
                if command:
                    max_cmd = self._terminal_width - 20
                    if len(command) > max_cmd:
                        command = command[: max_cmd - 3] + "..."
                    subtitle = f"$ {command}"
                else:
                    subtitle = args_str
            else:
                subtitle = args_str

        return title, subtitle

    def _rebuild_content(self) -> None:
        """Rebuild content with current tool calls."""
        # This is called to trigger a re-render
        pass

    def measure(self, available_width: int, available_height: int) -> Size:
        """Measure the space needed for this component.

        Args:
            available_width: Maximum width available
            available_height: Maximum height available

        Returns:
            Size needed for rendering
        """
        # Render at available width and count lines
        lines = self.render(available_width)
        height = len(lines)
        width = available_width

        # Calculate actual width needed
        for line in lines:
            # Strip ANSI codes for width calculation
            clean_line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            width = max(width, len(clean_line))

        return Size(min(width, available_width), min(height, available_height))

    def render(self, width: int | None = None) -> list[str]:
        """Render the message panel.

        Args:
            width: Width to render at (defaults to terminal_width)

        Returns:
            List of rendered lines
        """
        if width is None:
            width = self._terminal_width

        # Ensure minimum width
        width = max(width, 20)

        # Calculate content width for inner rendering
        content_width = width - 4  # Account for "│ " and " │"

        # Build all content lines
        all_content_lines: list[str] = []

        # Add error line if present
        if self._error:
            all_content_lines.append(f"{RED}Error: {self._error}{RESET}")

        # Sort tool calls by sequence
        sorted_tools = sorted(self._tool_calls, key=lambda tc: (tc.insert_position, tc.sequence))

        # Build content with tools interleaved
        text_parts: list[tuple[str, list[ToolCallInfo]]] = []
        last_position = 0

        for tool_call in sorted_tools:
            # Add text segment before this tool
            if tool_call.insert_position > last_position:
                text_segment = self._text_content[last_position : tool_call.insert_position]
                text_parts.append((text_segment, []))

            # Mark position for tool call
            text_parts.append(("", [tool_call]))
            last_position = tool_call.insert_position

        # Add remaining text
        if last_position < len(self._text_content):
            text_parts.append((self._text_content[last_position:], []))

        # If no tool calls, just add all text
        if not sorted_tools:
            text_parts = [(self._text_content, [])]

        # Render each segment
        for text_segment, tools in text_parts:
            # Render text segment
            if text_segment:
                if self._use_markdown and self._renderer and text_segment.strip():
                    rendered = self._renderer.render_markdown(text_segment)
                else:
                    rendered = text_segment

                # Split into lines and add
                for line in rendered.split("\n"):
                    # Ensure line fits in content width
                    if len(line) > content_width:
                        line = line[: content_width - 3] + "..."
                    all_content_lines.append(line)

            # Render tool calls
            for tool_call in tools:
                tool_lines = self._build_tool_call_lines(tool_call, content_width)
                all_content_lines.extend(tool_lines)

        # Build the outer box
        result = build_bordered_box(
            lines=all_content_lines,
            width=width,
            color=self._border_color,
            title=self._title,
        )

        return result

    def _build_tool_call_lines(self, tool_call: ToolCallInfo, max_width: int) -> list[str]:
        """Build lines for a tool call display.

        Args:
            tool_call: Tool call to display
            max_width: Maximum width for the tool box

        Returns:
            List of formatted lines
        """
        title, subtitle = self._get_tool_display_info(tool_call)

        # Build content lines
        lines: list[str] = []

        # Title line
        if subtitle:
            lines.append(f"{title} {DIM}{subtitle}{RESET}")
        else:
            lines.append(title)

        # Output (truncated unless expanded)
        if tool_call.output:
            output = tool_call.output if self._expanded else tool_call.output[:200] if len(tool_call.output) > 200 else tool_call.output

            lines.append(f"{DIM}{output}{RESET}")

        # Determine box color
        box_color = self._border_color
        if tool_call.status == "error":
            box_color = RED

        # Calculate box width
        if self._terminal_width <= self.NARROW_WIDTH:
            box_width = min(max_width - 2, 40)
        elif self._terminal_width <= self.MEDIUM_WIDTH:
            box_width = min(max_width - 2, 60)
        else:
            box_width = min(max_width - 2, 80)

        box_width = max(box_width, 20)

        return build_bordered_box(
            lines=lines,
            width=box_width,
            color=box_color,
            title="",
        )
