"""MessagePanel component for displaying conversation messages."""

from __future__ import annotations

from typing import Literal

from pypitui import BorderedBox, Text  # type: ignore

from src.interfaces.ansi import BOLD, CYAN, DIM, GREEN, RED, RESET
from src.interfaces.pypitui.models import ToolCallInfo


class MessagePanel(BorderedBox):  # type: ignore[misc]
    """A bordered panel for displaying conversation messages.

    Uses different border colors based on role:
    - user: cyan border, title "You"
    - assistant: green border, title "Alfred"
    - system: dim border, title "System"
    - error: red border (after set_error() called)

    Supports embedded tool call boxes for inline tool display.
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
        self._renderer: RichRenderer | None = None
        if use_markdown:
            from src.interfaces.pypitui.rich_renderer import RichRenderer

            self._renderer = RichRenderer(width=max(40, terminal_width - 4))

        # Tool calls embedded in this message
        self._tool_calls: list[ToolCallInfo] = []

        # Set title based on role
        title = {"user": "You", "assistant": "Alfred", "system": "System"}.get(role, "Alfred")
        self.set_title(title)

        # Set border color based on role
        self._set_border_color(role)

        # Build initial content (with markdown and ANSI placeholders if enabled)
        self._rebuild_content()

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
        # Use text length as insert position, but add sequence number to
        # disambiguate when multiple tools are added at the same position.
        # This ensures tools render in order even when called before text arrives.
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

    def finalize_tool_call(self, tool_call_id: str, status: Literal["success", "error"]) -> None:
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

    def set_terminal_width(self, width: int) -> None:
        """Update terminal width and rebuild if changed.

        Args:
            width: New terminal width
        """
        if width != self._terminal_width:
            self._terminal_width = width
            # Update renderer width if exists
            if self._renderer:
                self._renderer.update_width(max(40, width - 4))
            self._rebuild_content()

    def _rebuild_content(self) -> None:
        """Rebuild the content with embedded tool call boxes."""
        from src.interfaces.ansi import apply_ansi

        self.clear()

        if not self._tool_calls:
            # Simple case: no tool calls
            # First replace {cyan} etc. with ANSI codes, then apply markdown
            text_with_ansi = apply_ansi(self._text_content)
            display_text = text_with_ansi
            # Use Rich markdown rendering if enabled
            if self._use_markdown and self._renderer:
                try:
                    display_text = self._renderer.render_markdown(text_with_ansi)
                except Exception:
                    # Fallback to plain text on error
                    display_text = text_with_ansi
            self.add_child(Text(display_text, padding_x=0))
        else:
            # Build content with tool boxes inline
            self._build_content_with_tools()

    def _build_content_with_tools(self) -> None:
        """Build content string with tool call boxes embedded."""
        from src.interfaces.ansi import apply_ansi
        from src.interfaces.pypitui.box_utils import build_bordered_box
        from src.interfaces.pypitui.constants import DIM_BLUE, DIM_GREEN, DIM_RED

        # Build the full content with tool boxes as inline text
        parts: list[str] = []

        # Sort tool calls by (position, sequence) to maintain order
        sorted_tools = sorted(self._tool_calls, key=lambda t: (t.insert_position, t.sequence))

        # Tool box width: terminal width minus panel borders (2) and padding (2)
        box_width = max(20, self._terminal_width - 4)

        # Lazy import RichRenderer for tool output formatting
        renderer = None
        if self._use_markdown and self._renderer:
            renderer = self._renderer

        def render_segment(text: str) -> str:
            """Render text segment with markdown if enabled."""
            if not text:
                return text
            text_with_ansi = apply_ansi(text)
            if renderer:
                try:
                    return renderer.render_markdown(text_with_ansi)
                except Exception:
                    pass
            return text_with_ansi

        last_pos = 0
        for tc in sorted_tools:
            # Add text before this tool (with markdown rendering)
            if last_pos < tc.insert_position:
                segment = self._text_content[last_pos : tc.insert_position]
                parts.append(render_segment(segment))

            # Add tool box with consistent borders
            color = {"running": DIM_BLUE, "success": DIM_GREEN, "error": DIM_RED}.get(
                tc.status, DIM_BLUE
            )

            # Build tool box lines with Rich formatting
            content_lines: list[str] = []

            # Add arguments as first line (NEW)
            if tc.arguments:
                args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())
                # Truncate if too long
                if len(args_str) > 60:
                    args_str = args_str[:57] + "..."
                content_lines.append(f"{DIM}{args_str}{RESET}")
                content_lines.append("")  # Empty line after args

            if tc.output:
                # Truncate output for display (show beginning, not end)
                display_output = tc.output[:200] if len(tc.output) > 200 else tc.output

                # Try to format as JSON if applicable
                formatted_output = self._format_tool_output(display_output, renderer)
                content_lines = content_lines + formatted_output.split("\n")

            # Bold tool name in title using ANSI constants, then restore box color
            fancy_title = f"{BOLD}{tc.tool_name}{RESET}{color}"

            box_lines = build_bordered_box(
                lines=content_lines,
                width=box_width,
                color=color,
                title=fancy_title,
                center=False,
            )
            parts.append("\n" + "\n".join(box_lines) + "\n")

            last_pos = tc.insert_position

        # Add remaining text after last tool (with markdown rendering)
        if last_pos < len(self._text_content):
            segment = self._text_content[last_pos:]
            parts.append(render_segment(segment))

        content = "".join(parts)
        self.add_child(Text(content, padding_x=0))

    def _format_tool_output(self, output: str, renderer):  # type: ignore[no-untyped-def]
        """Format tool output with Rich markup if possible.

        Args:
            output: Raw tool output
            renderer: Optional RichRenderer for formatting

        Returns:
            Formatted output string
        """
        if not output:
            return output

        # Try to detect and format JSON
        stripped = output.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                import json

                parsed = json.loads(stripped)
                # Pretty print JSON
                pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                if renderer:
                    # Wrap in markdown code block for syntax highlighting
                    return renderer.render_markdown(f"```json\n{pretty_json}\n```")
                return pretty_json
            except json.JSONDecodeError:
                pass

        # Try to detect and format JSON arrays
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                import json

                parsed = json.loads(stripped)
                pretty_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                if renderer:
                    return renderer.render_markdown(f"```json\n{pretty_json}\n```")
                return pretty_json
            except json.JSONDecodeError:
                pass

        # For plain text, just return as-is (renderer will handle ANSI if enabled)
        if renderer and output:
            try:
                # Try to render any markup in the output
                return renderer.render_markup(f"[dim]{output}[/dim]")
            except Exception:
                pass

        return output

    @property
    def tool_calls(self) -> list[ToolCallInfo]:
        """Get list of tool calls in this message."""
        return self._tool_calls

    @property
    def _content(self) -> str:
        """Get the text content (backwards compat)."""
        return self._text_content
