"""Tab completion for LiveDisplay."""

from collections.abc import Callable
from pathlib import Path

from rich.text import Text


class Completer:
    """Tab completion with fuzzy matching for commands, tools, and file paths."""

    STATIC_COMMANDS = [
        "/help",
        "/session",
        "/sessions",
        "/new",
        "/model",
        "/clear",
        "/exit",
        "/quit",
    ]

    TOOLS = [
        "remember",
        "forget",
        "search",
        "bash",
        "read",
        "write",
        "edit",
        "schedule",
        "approve",
        "reject",
        "list",
    ]

    def __init__(
        self,
        max_visible: int = 5,
        get_session_ids: Callable[[], list[str]] | None = None,
    ) -> None:
        self.max_visible = max_visible
        self.get_session_ids = get_session_ids
        self.matches: list[str] = []
        self.selected_index: int = 0
        self._visible: bool = False

    def _fuzzy_match(self, query: str, candidate: str) -> bool:
        query = query.lower()
        candidate = candidate.lower()
        q_idx = 0
        for char in candidate:
            if q_idx < len(query) and char == query[q_idx]:
                q_idx += 1
        return q_idx == len(query)

    def _score_match(self, query: str, candidate: str) -> int:
        query = query.lower()
        candidate = candidate.lower()
        if candidate == query:
            return 100
        if candidate.startswith(query):
            return 80
        score = 50
        q_idx = 0
        for i, char in enumerate(candidate):
            if q_idx < len(query) and char == query[q_idx]:
                score += max(0, 10 - i)
                q_idx += 1
        return score

    def get_completions(self, text: str) -> list[str]:
        if not text:
            return []

        if text.startswith("/"):
            if text.startswith("/resume ") and self.get_session_ids:
                candidates = [f"/resume {sid}" for sid in self.get_session_ids()]
                query = text
            else:
                candidates = self.STATIC_COMMANDS
                query = text
        elif " " not in text:
            candidates = self.TOOLS
            query = text
        else:
            last_word = text.split()[-1]
            if "/" in last_word or last_word.startswith("~"):
                candidates = self._get_file_completions(last_word)
                query = last_word
            else:
                candidates = self.TOOLS
                query = last_word

        scored = []
        for candidate in candidates:
            if self._fuzzy_match(query, candidate):
                score = self._score_match(query, candidate)
                scored.append((score, candidate))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [c for _, c in scored]

    def _get_file_completions(self, partial: str) -> list[str]:
        try:
            expanded = Path(partial).expanduser()
            if partial.endswith("/"):
                dir_path = expanded
                prefix = ""
            else:
                dir_path = expanded.parent
                prefix = expanded.name

            if not dir_path.exists():
                return []

            results = []
            for item in dir_path.iterdir():
                name = item.name
                if name.startswith("."):
                    continue
                if item.is_dir():
                    name += "/"
                results.append(str(dir_path / name))

            if prefix:
                results = [r for r in results if Path(r).name.startswith(prefix)]

            return sorted(results)
        except (OSError, PermissionError):
            return []

    def start(self, text: str) -> bool:
        self.matches = self.get_completions(text)
        if self.matches:
            self.selected_index = 0
            self._visible = True
            return True
        return False

    def next(self) -> None:
        if self.matches:
            self.selected_index = (self.selected_index + 1) % len(self.matches)

    def prev(self) -> None:
        if self.matches:
            self.selected_index = (self.selected_index - 1) % len(self.matches)

    def get_selected(self) -> str | None:
        if self.matches and 0 <= self.selected_index < len(self.matches):
            return self.matches[self.selected_index]
        return None

    def hide(self) -> None:
        self._visible = False
        self.matches = []
        self.selected_index = 0

    @property
    def visible(self) -> bool:
        return self._visible and len(self.matches) > 0

    def render_dropdown(self) -> Text:
        if not self.visible:
            return Text()

        # Box drawing characters
        top_left = "╭"
        top_right = "╮"
        bottom_left = "╰"
        bottom_right = "╯"
        horizontal = "─"
        vertical = "│"
        pointer = "▸ "

        # Calculate visible matches
        start = 0
        if len(self.matches) > self.max_visible:
            start = max(0, self.selected_index - self.max_visible // 2)
            start = min(start, len(self.matches) - self.max_visible)

        visible_matches = self.matches[start : start + self.max_visible]

        # Calculate width based on longest match
        max_width = max(len(m) for m in visible_matches) if visible_matches else 0
        max_width = min(max_width, 50)  # Cap at 50 chars
        inner_width = max_width + 4  # Space for pointer and padding

        # Build the dropdown
        text = Text()

        # Top border with title
        text.append(top_left, style="cyan")
        text.append(horizontal * 2, style="cyan")
        text.append("commands", style="bold cyan")
        text.append(horizontal * (inner_width - 10), style="cyan")
        text.append(top_right, style="cyan")
        text.append("\n")

        # Match rows
        for i, match in enumerate(visible_matches):
            actual_index = start + i
            is_selected = actual_index == self.selected_index
            display = match[:50]  # Truncate if too long
            padding = " " * (inner_width - len(display) - 2)

            text.append(vertical, style="cyan")
            if is_selected:
                text.append(pointer, style="bold cyan")
                text.append(display, style="bold white")
                text.append(padding)
            else:
                text.append("  ", style="dim")
                text.append(display, style="dim")
                text.append(padding, style="dim")
            text.append(vertical, style="cyan")
            text.append("\n")

        # Bottom border with count
        text.append(bottom_left, style="cyan")
        count_text = f" {self.selected_index + 1}/{len(self.matches)} "
        remaining_width = inner_width - len(count_text)
        text.append(horizontal * remaining_width, style="cyan")
        text.append(count_text, style="dim cyan")
        text.append(bottom_right, style="cyan")

        return text
