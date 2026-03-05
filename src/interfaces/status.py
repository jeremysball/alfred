"""Status line rendering for CLI interface."""

from dataclasses import dataclass, field
from itertools import cycle
from typing import Any

from prompt_toolkit.formatted_text import FormattedText
from rich.console import Group, RenderableType
from rich.text import Text

from src.token_tracker import TokenUsage

# Spinner frames for activity indicator (braille dots)
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


@dataclass
class StatusData:
    """Current state for status line display."""

    model_name: str
    usage: TokenUsage
    context_tokens: int
    memories_count: int = 0
    session_messages: int = 0
    prompt_sections: list[str] = field(default_factory=list)
    is_streaming: bool = False
    _spinner_cycle: Any = field(init=False, repr=False, compare=False)
    _current_frame: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Initialize defaults and spinner cycle."""
        self._spinner_cycle = cycle(SPINNER_FRAMES)
        self._current_frame = ">"

    def next_spinner_frame(self) -> str:
        """Get next spinner frame for animation."""
        if self.is_streaming:
            self._current_frame = next(self._spinner_cycle)
        else:
            self._current_frame = ">"
        return self._current_frame


class StatusRenderer:
    """Renders status line for CLI display.

    Format:
    > kimi/moonshot-v1-128k │ in:12K out:3K cache:8K reason:1K │ ctx:45
    📚 3 memories │ 💬 28 msgs │ 📋 SOUL,USER,TOOLS
    """

    def __init__(self, status_data: StatusData) -> None:
        self.status = status_data

    def render(self) -> RenderableType:
        """Render the status display as a Group of lines."""
        return Group(self._render_token_line(), self._render_context_line())

    def to_prompt_toolkit(self) -> Any:
        """Render status for prompt_toolkit bottom toolbar.

        Returns FormattedText tuple list for bottom_toolbar.
        """
        frame = self.status.next_spinner_frame()
        spinner_style = "cyan" if self.status.is_streaming else "green"

        sections_str = (
            ",".join(self.status.prompt_sections) if self.status.prompt_sections else "none"
        )
        # Truncate sections if too long to fit in toolbar
        if len(sections_str) > 20:
            sections_str = sections_str[:17] + "..."

        # Build token parts - only include cache/reason if non-zero
        token_parts = [
            ("", f"in:{self._format_number(self.status.usage.input_tokens)} "),
            ("", f"out:{self._format_number(self.status.usage.output_tokens)}"),
        ]
        if self.status.usage.cache_read_tokens > 0:
            cache = self._format_number(self.status.usage.cache_read_tokens)
            token_parts.append(("", f" cache:{cache}"))
        if self.status.usage.reasoning_tokens > 0:
            reason = self._format_number(self.status.usage.reasoning_tokens)
            token_parts.append(("", f" reason:{reason}"))

        # Build as single line for toolbar
        parts = [
            (spinner_style, f"{frame} "),
            ("bold", self.status.model_name),
            ("", " | "),
            *token_parts,
            ("", f" | ctx:{self._format_number(self.status.context_tokens)}"),
        ]

        m = self.status.memories_count
        s = self.status.session_messages
        parts.append(("", f"  📚 {m} | 💬 {s} | 📋 {sections_str}"))

        return FormattedText(parts)

    def _render_token_line(self) -> Text:
        """Render the token/model status line."""
        text = Text()

        # Activity indicator
        frame = self.status.next_spinner_frame()
        if self.status.is_streaming:
            text.append(frame, style="cyan")
        else:
            text.append(frame, style="green")
        text.append(" ")

        # Model name
        text.append(self.status.model_name, style="bold white")
        text.append(" | ", style="dim")

        # Token counts
        text.append("in:", style="dim")
        text.append(f"{self._format_number(self.status.usage.input_tokens)}", style="blue")
        text.append(" ")

        text.append("out:", style="dim")
        text.append(f"{self._format_number(self.status.usage.output_tokens)}", style="green")
        text.append(" ")

        # Cache read (only if non-zero)
        if self.status.usage.cache_read_tokens > 0:
            text.append("cache:", style="dim")
            val = self._format_number(self.status.usage.cache_read_tokens)
            text.append(val, style="yellow")
            text.append(" ")

        # Reasoning_tokens (only if non-zero)
        if self.status.usage.reasoning_tokens > 0:
            text.append("reason:", style="dim")
            val = self._format_number(self.status.usage.reasoning_tokens)
            text.append(val, style="magenta")
            text.append(" ")

        text.append("| ctx:", style="dim")
        text.append(f"{self._format_number(self.status.context_tokens)}", style="white")

        return text

    def _render_context_line(self) -> Text:
        """Render the context summary line."""
        text = Text()

        # Memories count
        text.append("📚 ", style="white")
        text.append(f"{self.status.memories_count}", style="yellow")
        text.append(" memories", style="dim")

        text.append(" | ", style="dim")

        # Session messages
        text.append("💬 ", style="white")
        text.append(f"{self.status.session_messages}", style="cyan")
        text.append(" msgs", style="dim")

        text.append(" | ", style="dim")

        # Prompt sections
        text.append("📋 ", style="white")
        if self.status.prompt_sections:
            text.append(",".join(self.status.prompt_sections), style="green")
        else:
            text.append("none", style="dim")

        return text

    @staticmethod
    def _format_number(n: int) -> str:
        """Format number with K suffix for thousands."""
        if n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(n)
