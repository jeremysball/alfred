"""Status line rendering for CLI interface."""

from dataclasses import dataclass
from itertools import cycle

from rich.text import Text

from src.token_tracker import TokenUsage

# Spinner frames for activity indicator
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


@dataclass
class StatusData:
    """Current state for status line display."""

    model_name: str
    usage: TokenUsage
    context_tokens: int
    is_streaming: bool = False

    def __post_init__(self) -> None:
        """Initialize spinner cycle."""
        self._spinner_cycle = cycle(SPINNER_FRAMES)
        self._current_frame = "●"

    def next_spinner_frame(self) -> str:
        """Get next spinner frame for animation."""
        if self.is_streaming:
            self._current_frame = next(self._spinner_cycle)
        else:
            self._current_frame = "●"
        return self._current_frame


class StatusRenderer:
    """Renders status line for CLI display.

    Format:
    🔄 kimi/moonshot-v1-128k │ 📥 12,847 📤 3,291 💾 8,420 🧠 1,200 │ Context: 45
    """

    def __init__(self, status_data: StatusData) -> None:
        self.status = status_data

    def render(self) -> Text:
        """Render the status line as Rich Text."""
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
        text.append(" │ ", style="dim")

        # Token counts
        text.append("📥 ", style="default")
        text.append(f"{self._format_number(self.status.usage.input_tokens)}", style="blue")
        text.append(" ")

        text.append("📤 ", style="default")
        text.append(f"{self._format_number(self.status.usage.output_tokens)}", style="green")
        text.append(" ")

        # Cache read (only if non-zero)
        if self.status.usage.cache_read_tokens > 0:
            text.append("💾 ", style="default")
            text.append(
                f"{self._format_number(self.status.usage.cache_read_tokens)}", style="yellow"
            )
            text.append(" ")

        # Reasoning tokens (only if non-zero)
        if self.status.usage.reasoning_tokens > 0:
            text.append("🧠 ", style="default")
            text.append(
                f"{self._format_number(self.status.usage.reasoning_tokens)}", style="magenta"
            )
            text.append(" ")

        text.append("│ Context: ", style="dim")
        text.append(f"{self._format_number(self.status.context_tokens)}", style="white")

        return text

    @staticmethod
    def _format_number(n: int) -> str:
        """Format number with K suffix for thousands."""
        if n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(n)
