"""MessagePanel component for displaying conversation messages."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal, cast

from alfred.interfaces.ansi import BOLD, CYAN, DIM, GREEN, RED, RESET
from alfred.interfaces.pypitui.models import ToolCallInfo
from pypitui import BorderedBox
from pypitui.utils import visible_width


@dataclass
class ContentBlock:
    """A block of content - either text or a tool call."""

    type: Literal["text", "tool"]
    content: str = ""
    tool_info: ToolCallInfo | None = None


class MessagePanel(BorderedBox):
    """A bordered panel for displaying conversation messages with embedded tool calls.

    Uses different border colors based on role:
    - user: cyan border, title "You"
    - assistant: green border, title "Alfred"
    - system: dim border, title "System"
    - error: red border (after set_error() called)

    Supports embedded tool call boxes for inline tool display.
    Tool calls are rendered as separate blocks to prevent text wrapping issues.

    Future: Supports Ctrl-T expansion of tool calls.
    """

    def __init__(
        self,
        role: Literal["user", "assistant", "system"],
        content: str = "",
        *,
        padding_x: int = 1,
        padding_y: int = 0,
        terminal_width: int = 80,
        use_markdown: bool = True,
    ) -> None:
        """Initialize the message panel.

        Args:
            role: "user", "assistant", or "system"
            content: Initial message content
            padding_x: Horizontal padding inside border
            padding_y: Vertical padding inside border
            terminal_width: Current terminal width for box sizing
            use_markdown: Enable Rich markdown rendering
        """
        super().__init__(padding_x=padding_x, padding_y=padding_y)

        self._role = role
        self._text_content = content
        self._is_error = False
        self._border_color = GREEN
        self._terminal_width = terminal_width
        self._use_markdown = use_markdown

        # Create RichRenderer if markdown enabled
        # Width must account for nested tool call boxes:
        # - MessagePanel borders: 2 chars
        # - Tool box borders: 2 chars
        # - Tool box padding: 2 chars (1 on each side)
        # So tool content width = terminal_width - 8
        self._renderer: Any = None
        if use_markdown:
            from alfred.interfaces.pypitui.rich_renderer import RichRenderer

            renderer_width = max(20, terminal_width - 8)
            self._renderer = RichRenderer(width=renderer_width)

        # Tool calls embedded in this message
        self._tool_calls: list[ToolCallInfo] = []

        # Content blocks for mixed rendering
        self._content_blocks: list[ContentBlock] = []

        # Set title based on role
        title = {"user": "You", "assistant": "Alfred", "system": "System"}.get(role, "Alfred")
        self.set_title(title)

        # Set border color based on role
        self._set_border_color(role)

        # Build initial content
        self._compose_content()

    def _set_border_color(self, role_or_state: str) -> None:
        """Set border color by overriding class border characters.

        Args:
            role_or_state: "user", "assistant", "system", or "error"
        """
        color = {"user": CYAN, "assistant": GREEN, "system": DIM, "error": RED}.get(
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

    def set_content(self, text: str) -> None:
        """Update the message content.

        Args:
            text: New content text
        """
        self._text_content = text
        self._compose_content()
        # Invalidate render cache so new content appears
        self._cache = None

    def set_error(self, error_msg: str) -> None:
        """Set panel to error state with red border.

        Args:
            error_msg: Error message to display
        """
        self._is_error = True
        self._set_border_color("error")
        self.set_content(f"Error: {error_msg}")

    # --- Tool Call Methods ---

    def add_tool_call(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict[str, object] | None = None,
    ) -> None:
        """Add an embedded tool call box at current text position.

        Args:
            tool_name: Name of the tool
            tool_call_id: Unique ID for this tool call
            arguments: Optional tool arguments (dict of key=value pairs)
        """
        insert_position = len(self._text_content)
        sequence = len(self._tool_calls)

        tool_info = ToolCallInfo(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            insert_position=insert_position,
            sequence=sequence,
            arguments=arguments,
        )
        self._tool_calls.append(tool_info)
        self._compose_content()
        self._cache = None

    def update_tool_call(self, tool_call_id: str, output: str) -> None:
        """Update output for a tool call.

        Args:
            tool_call_id: ID of the tool call to update
            output: New output text to append
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.output = output
                self._compose_content()
                self._cache = None
                return

    def finalize_tool_call(self, tool_call_id: str, status: Literal["success", "error"]) -> None:
        """Set final status for a tool call.

        Args:
            tool_call_id: ID of the tool call to finalize
            status: Final status (success or error)
        """
        for tc in self._tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.status = status
                self._compose_content()
                self._cache = None
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

    def restore_tool_calls(self, tool_calls: list[ToolCallInfo] | None) -> None:
        """Restore tool calls from stored ToolCallInfo objects.

        Args:
            tool_calls: List of ToolCallInfo objects to restore
        """
        if not tool_calls:
            return

        self._tool_calls = list(tool_calls)
        self._compose_content()
        self._cache = None

    def restore_tool_calls_from_records(self, tool_calls: list[Any] | None) -> None:
        """Restore tool calls from session ToolCallRecord objects."""
        if not tool_calls:
            return

        tool_infos: list[ToolCallInfo] = []
        for tc in tool_calls:
            if hasattr(tc, "tool_call_id"):
                tool_info = ToolCallInfo(
                    tool_name=tc.tool_name,
                    tool_call_id=tc.tool_call_id,
                    output=tc.output,
                    status=tc.status,
                    insert_position=tc.insert_position,
                    sequence=tc.sequence,
                    arguments=tc.arguments if tc.arguments else {},
                )
            else:
                tool_info = ToolCallInfo(
                    tool_name=tc.get("tool_name", "unknown"),
                    tool_call_id=tc.get("tool_call_id", ""),
                    output=tc.get("output", ""),
                    status=tc.get("status", "success"),
                    insert_position=tc.get("insert_position", 0),
                    sequence=tc.get("sequence", 0),
                    arguments=tc.get("arguments") or {},
                )
            tool_infos.append(tool_info)

        self.restore_tool_calls(tool_infos)

    def set_terminal_width(self, width: int) -> None:
        """Update terminal width and rebuild if changed.

        Args:
            width: New terminal width
        """
        if width != self._terminal_width:
            self._terminal_width = width
            if self._renderer:
                self._renderer.update_width(max(20, width - 8))
            self._compose_content()

    def _compose_content(self) -> None:
        """Compose content blocks from text and tool calls."""
        from alfred.interfaces.ansi import apply_ansi

        self._content_blocks = []

        if not self._tool_calls:
            # Simple case: no tool calls
            text = apply_ansi(self._text_content)
            if self._use_markdown and self._renderer:
                with suppress(Exception):
                    text = self._renderer.render_markdown(text)
            self._content_blocks.append(ContentBlock(type="text", content=text))
        else:
            # Mixed case: text with embedded tool calls
            sorted_tools = sorted(
                self._tool_calls, key=lambda t: (t.insert_position, t.sequence)
            )

            last_pos = 0
            for tc in sorted_tools:
                # Add text before this tool
                if last_pos < tc.insert_position:
                    segment = self._text_content[last_pos : tc.insert_position]
                    if segment:
                        text = apply_ansi(segment)
                        if self._use_markdown and self._renderer:
                            with suppress(Exception):
                                text = self._renderer.render_markdown(text)
                        self._content_blocks.append(
                            ContentBlock(type="text", content=text)
                        )

                # Add tool call block
                self._content_blocks.append(
                    ContentBlock(type="tool", content="", tool_info=tc)
                )
                last_pos = tc.insert_position

            # Add remaining text after last tool
            if last_pos < len(self._text_content):
                segment = self._text_content[last_pos:]
                text = apply_ansi(segment)
                if self._use_markdown and self._renderer:
                    with suppress(Exception):
                        text = self._renderer.render_markdown(text)
                self._content_blocks.append(ContentBlock(type="text", content=text))

    def _build_tool_box(self, tool_info: ToolCallInfo) -> list[str]:
        """Build a tool call box as list of lines.

        Args:
            tool_info: Tool call information

        Returns:
            List of rendered lines for the tool box
        """
        from alfred.interfaces.pypitui.box_utils import build_bordered_box
        from alfred.interfaces.pypitui.constants import DIM_BLUE, DIM_GREEN, DIM_RED

        color = {"running": DIM_BLUE, "success": DIM_GREEN, "error": DIM_RED}.get(
            tool_info.status, DIM_BLUE
        )

        # Tool box width: terminal width minus panel borders (2) and padding (2)
        box_width = max(20, self._terminal_width - 4)

        content_lines: list[str] = []

        # Add arguments
        if tool_info.arguments:
            args_str = ", ".join(f"{k}={v}" for k, v in tool_info.arguments.items())
            content_lines.append(f"{DIM}{args_str}{RESET}")
            content_lines.append("")

        # Add output if any
        if tool_info.output:
            display_output = (
                tool_info.output[:200] if len(tool_info.output) > 200 else tool_info.output
            )
            formatted = self._format_tool_output(display_output)
            content_lines.extend(formatted.split("\n"))

        fancy_title = f"{BOLD}{tool_info.tool_name}{RESET}{color}"
        return build_bordered_box(
            lines=content_lines,
            width=box_width,
            color=color,
            title=fancy_title,
            center=False,
        )

    def _format_tool_output(self, output: str) -> str:
        """Format tool output with Rich markup if possible.

        Args:
            output: Raw tool output

        Returns:
            Formatted output string
        """
        if not output:
            return output

        import json

        stripped = output.strip()

        # Try to detect and format JSON
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                if self._renderer:
                    return cast(str, self._renderer.render_markdown(f"```json\n{pretty_json}\n```"))
                return pretty_json
            except json.JSONDecodeError:
                pass

        # Try to detect and format JSON arrays
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
                pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                if self._renderer:
                    return cast(str, self._renderer.render_markdown(f"```json\n{pretty_json}\n```"))
                return pretty_json
            except json.JSONDecodeError:
                pass

        # Check for markdown code blocks
        if "```" in output:
            if self._renderer:
                try:
                    return cast(str, self._renderer.render_markdown(output))
                except Exception:
                    pass
            return output

        # For plain text, use dim styling
        if self._renderer and output:
            try:
                return cast(str, self._renderer.render_markup(f"[dim]{output}[/dim]"))
            except Exception:
                pass

        return output

    def _render_text_block(self, text: str, width: int) -> list[str]:
        """Render a text block by wrapping it to the given width.

        Args:
            text: Text content to render
            width: Width to wrap to

        Returns:
            List of wrapped lines
        """
        from pypitui.utils import wrap_text_with_ansi

        if not text:
            return []

        # Wrap text preserving ANSI codes
        return wrap_text_with_ansi(text, width)

    def render(self, width: int) -> list[str]:
        """Render the message panel with mixed content.

        Overrides BorderedBox.render to handle mixed text and tool call blocks.

        Args:
            width: Width to render at

        Returns:
            List of rendered lines
        """
        # Check cache
        if self._cache and self._cache[0] == width:
            return self._cache[1]

        # Calculate content width (inside borders and padding)
        padding_x: int = getattr(self, "_padding_x", 0)
        content_width = max(1, width - 2 - padding_x * 2)

        # Build content lines from blocks
        content_lines: list[str] = []

        for block in self._content_blocks:
            if block.type == "text":
                # Render text block
                if block.content:
                    text_lines = self._render_text_block(block.content, content_width)
                    # Pad each line to content_width
                    for line in text_lines:
                        vwidth = visible_width(line)
                        if vwidth < content_width:
                            line = line + " " * (content_width - vwidth)
                        content_lines.append(line)
            elif block.type == "tool" and block.tool_info:
                # Render tool block as pre-formatted box lines
                tool_lines = self._build_tool_box(block.tool_info)
                # Pad each line to content_width to maintain alignment
                for line in tool_lines:
                    vwidth = visible_width(line)
                    if vwidth < content_width:
                        line = line + " " * (content_width - vwidth)
                    content_lines.append(line)

        # Build the bordered output
        lines: list[str] = []

        # Top border
        top_border = self.TOP_LEFT + self.HORIZONTAL * (width - 2) + self.TOP_RIGHT
        lines.append(top_border)

        # Top padding
        lines.extend(
            self.VERTICAL + " " * (width - 2) + self.VERTICAL
            for _ in range(getattr(self, "_padding_y", 0))
        )

        # Title if provided
        title_val: str | None = getattr(self, "_title", None)
        if title_val:
            padding_x_val: int = getattr(self, "_padding_x", 0)
            title_padded = " " * padding_x_val + title_val + " " * padding_x_val
            inner_width = width - 2
            if visible_width(title_padded) < inner_width:
                title_padded += " " * (inner_width - visible_width(title_padded))
            lines.append(self.VERTICAL + title_padded + self.VERTICAL)
            sep_inner = self.HORIZONTAL * inner_width
            lines.append(self.T_LEFT + sep_inner + self.T_RIGHT)

        # Content lines with padding
        for content_line in content_lines:
            padding = " " * getattr(self, "_padding_x", 0)
            right_padding = " " * getattr(self, "_padding_x", 0)
            lines.append(self.VERTICAL + padding + content_line + right_padding + self.VERTICAL)

        # Bottom padding
        lines.extend(
            self.VERTICAL + " " * (width - 2) + self.VERTICAL
            for _ in range(getattr(self, "_padding_y", 0))
        )

        # Bottom border
        bottom_border = self.BOTTOM_LEFT + self.HORIZONTAL * (width - 2) + self.BOTTOM_RIGHT
        lines.append(bottom_border)

        # Cache - use setattr to avoid type issues with inherited attribute
        cache_value: tuple[int, list[str]] = (width, lines)
        self._cache = cache_value

        return lines

    @property
    def tool_calls(self) -> list[ToolCallInfo]:
        """Get list of tool calls in this message."""
        return self._tool_calls

    @property
    def content_blocks(self) -> list[ContentBlock]:
        """Get content blocks for inspection/testing."""
        return self._content_blocks

    @property
    def _content(self) -> str:
        """Get the text content (backwards compat)."""
        return self._text_content
